import hashlib
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.core.cache import cache
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, features

from apps.core.services.rtl import contains_arabic, shape_arabic


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "id_card"
FONT_DIR = ASSET_DIR / "fonts"

FONT_LATIN = FONT_DIR / "DejaVuSans.ttf"
FONT_LATIN_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_ARABIC = FONT_DIR / "NotoSansArabic-Regular.ttf"
FONT_ARABIC_BOLD = FONT_DIR / "NotoSansArabic-Bold.ttf"
LOGO_PATH = ASSET_DIR / "logo.jpg"
MIXED_ID_RUN_PATTERN = re.compile(r"[\u0600-\u06FF]+|[^\u0600-\u06FF]+")
RAQM_AVAILABLE = features.check("raqm")


@lru_cache(maxsize=128)
def _load_font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(maxsize=4)
def _prepared_logo(size):
    logo = Image.open(LOGO_PATH).convert("RGB")
    logo = ImageOps.fit(logo, (size, size), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return logo, mask


class IDCardGenerator:
    """Generate a print-ready CR80 student identity card at 300 DPI."""

    width = 1011
    height = 638

    navy = (9, 35, 67)
    blue = (26, 76, 145)
    royal_blue = (37, 82, 214)
    green = (27, 171, 83)
    orange = (229, 151, 65)
    earth = (106, 49, 13)
    slate = (71, 85, 105)
    text = (15, 23, 42)
    paper = (248, 250, 252)

    def __init__(self, student):
        self.student = student

    def generate(self) -> BytesIO:
        card = Image.new("RGB", (self.width, self.height), self.paper)
        draw = ImageDraw.Draw(card)
        self._draw_background(card, draw)
        self._draw_header(card, draw)
        self._draw_photo(card, draw)
        self._draw_identity(draw)
        self._draw_footer(draw)

        output = BytesIO()
        card.save(output, format="PNG", compress_level=4, dpi=(300, 300))
        output.seek(0)
        return output

    def generate_cached(self):
        cache_key = self.cache_key()
        image_bytes = cache.get(cache_key)
        if image_bytes is None:
            image_bytes = self.generate().getvalue()
            cache.set(cache_key, image_bytes, timeout=60 * 60 * 24)
        return image_bytes, cache_key

    def cache_key(self):
        academic_year, valid_until = self._academic_period()
        user = self.student.user
        photo = getattr(self.student, "photo", None)
        photo_name = getattr(photo, "name", "") if photo else ""
        source = "|".join([
            "student-card-v4",
            str(getattr(self.student, "pk", getattr(self.student, "id", ""))),
            str(getattr(self.student, "updated_at", "")),
            str(getattr(user, "updated_at", "")),
            self._full_name(),
            str(self.student.student_id),
            str(getattr(self.student.program, "name", "")),
            self._level_label(),
            str(getattr(self.student, "status", "")),
            photo_name,
            academic_year,
            valid_until,
        ])
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return f"student-id-card:{digest}"

    def _font(self, size, *, bold=False, arabic=False):
        if arabic:
            path = FONT_ARABIC_BOLD if bold else FONT_ARABIC
        else:
            path = FONT_LATIN_BOLD if bold else FONT_LATIN
        return _load_font(str(path), size)

    def _display_text(self, value):
        text = str(value or "").strip()
        if contains_arabic(text) and not RAQM_AVAILABLE:
            return shape_arabic(text)
        return text

    def _text_options(self, value, *, force_ltr=False):
        if not RAQM_AVAILABLE:
            return {}
        if force_ltr:
            return {"direction": "ltr", "language": "fr"}
        if contains_arabic(value) and not force_ltr:
            return {"direction": "rtl", "language": "ar"}
        return {}

    def _fit_font(self, draw, value, max_width, start_size, min_size, *, bold=True, force_ltr=False):
        arabic = contains_arabic(value) and not force_ltr
        display = self._display_text(value)
        for size in range(start_size, min_size - 1, -1):
            font = self._font(size, bold=bold, arabic=arabic)
            box = draw.textbbox(
                (0, 0),
                display,
                font=font,
                **self._text_options(value, force_ltr=force_ltr),
            )
            if box[2] - box[0] <= max_width:
                return display, font
        return display, self._font(min_size, bold=bold, arabic=arabic)

    def _draw_background(self, card, draw):
        for y in range(self.height):
            ratio = y / self.height
            color = tuple(
                round(self.paper[index] * (1 - ratio * 0.08) + (238, 245, 255)[index] * ratio * 0.08)
                for index in range(3)
            )
            draw.line((0, y, self.width, y), fill=color)

        decoration = Image.new("RGBA", card.size, (0, 0, 0, 0))
        deco_draw = ImageDraw.Draw(decoration)
        deco_draw.ellipse((720, 75, 1130, 485), fill=(*self.green, 16))
        deco_draw.ellipse((800, 150, 1070, 420), outline=(*self.orange, 35), width=12)
        deco_draw.polygon([(650, 178), (1011, 178), (1011, 320)], fill=(*self.blue, 10))
        card.paste(decoration, (0, 0), decoration)

    def _draw_header(self, card, draw):
        header_height = 174
        for y in range(header_height):
            ratio = y / max(header_height - 1, 1)
            color = tuple(
                round(self.navy[index] * (1 - ratio) + self.blue[index] * ratio)
                for index in range(3)
            )
            draw.line((0, y, self.width, y), fill=color)

        draw.polygon([(760, 0), (1011, 0), (1011, 174), (875, 174)], fill=(31, 94, 178))
        draw.rectangle((0, 174, self.width, 181), fill=self.orange)
        draw.rectangle((0, 181, self.width, 185), fill=self.green)

        self._paste_logo(card, 38, 23, 126)

        draw.text(
            (184, 35),
            "UNIVERSITÉ PRIVÉE ATTAWOUNE",
            font=self._font(29, bold=True),
            fill="white",
        )
        arabic_university_name = "جامعة التعاون الخاصة"
        draw.text(
            (720, 82),
            self._display_text(arabic_university_name),
            font=self._font(26, bold=True, arabic=True),
            fill=(204, 240, 218),
            anchor="ra",
            **self._text_options(arabic_university_name),
        )
        draw.text(
            (184, 126),
            "SAVOIR  •  EXCELLENCE  •  SERVICE",
            font=self._font(15, bold=True),
            fill=(191, 219, 254),
        )

        draw.rounded_rectangle((790, 49, 968, 126), radius=16, fill=(68, 116, 184), outline=(255, 255, 255), width=2)
        draw.text(
            (879, 73),
            "CARTE D'ÉTUDIANT",
            font=self._font(16, bold=True),
            fill="white",
            anchor="mm",
        )
        draw.text(
            (879, 104),
            "STUDENT ID CARD",
            font=self._font(12, bold=True),
            fill=(219, 234, 254),
            anchor="mm",
        )

    def _paste_logo(self, card, x, y, size):
        logo, mask = _prepared_logo(size)
        ring_size = size + 10
        ring = Image.new("RGBA", (ring_size, ring_size), (255, 255, 255, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, ring_size - 1, ring_size - 1), fill=(255, 255, 255, 245))
        card.paste(ring, (x - 5, y - 5), ring)
        card.paste(logo, (x, y), mask)

    def _draw_photo(self, card, draw):
        x, y, width, height = 44, 214, 238, 286
        self._draw_shadow(card, (x - 4, y - 4, x + width + 4, y + height + 4), 18)

        photo = self._load_photo((width, height))
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=20, fill=255)
        card.paste(photo, (x, y), mask)
        draw.rounded_rectangle(
            (x, y, x + width, y + height),
            radius=20,
            outline="white",
            width=7,
        )
        draw.rounded_rectangle(
            (x + 6, y + 6, x + width - 6, y + height - 6),
            radius=15,
            outline=self.green,
            width=3,
        )

        status = self._status_label()
        status_color = self.green if getattr(self.student, "status", "ACTIVE") == "ACTIVE" else self.orange
        draw.rounded_rectangle((69, 477, 257, 524), radius=23, fill=status_color)
        draw.ellipse((86, 495, 98, 507), fill="white")
        status_text, status_font = self._fit_font(draw, status.upper(), 125, 18, 13, bold=True)
        draw.text((107, 501), status_text, font=status_font, fill="white", anchor="lm")

    def _load_photo(self, size):
        photo_field = getattr(self.student, "photo", None)
        if photo_field:
            try:
                photo_field.open("rb")
                try:
                    photo = Image.open(photo_field).convert("RGB")
                    photo.load()
                finally:
                    photo_field.close()
                return ImageOps.fit(photo, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.38))
            except Exception:
                pass
        return self._photo_placeholder(size)

    def _photo_placeholder(self, size):
        placeholder = Image.new("RGB", size, (226, 232, 240))
        draw = ImageDraw.Draw(placeholder)
        for y in range(size[1]):
            ratio = y / size[1]
            color = tuple(
                round((226, 232, 240)[index] * (1 - ratio) + (203, 213, 225)[index] * ratio)
                for index in range(3)
            )
            draw.line((0, y, size[0], y), fill=color)
        initials = self._initials()
        display, font = self._fit_font(draw, initials, size[0] - 50, 74, 46, bold=True)
        draw.ellipse((52, 58, size[0] - 52, size[0] - 46), fill=(241, 245, 249))
        draw.text(
            (size[0] // 2, 136),
            display,
            font=font,
            fill=self.blue,
            anchor="mm",
            **self._text_options(initials),
        )
        draw.text(
            (size[0] // 2, size[1] - 48),
            "PHOTO",
            font=self._font(14, bold=True),
            fill=(100, 116, 139),
            anchor="mm",
        )
        return placeholder

    def _draw_identity(self, draw):
        full_name = self._full_name()
        program = str(getattr(self.student.program, "name", "") or "Non renseignée")
        level = self._level_label()

        draw.text(
            (325, 216),
            "IDENTITÉ DE L'ÉTUDIANT",
            font=self._font(14, bold=True),
            fill=self.green,
        )

        name_text, name_font = self._fit_font(draw, full_name, 625, 40, 25, bold=True)
        if contains_arabic(full_name):
            draw.text(
                (968, 248),
                name_text,
                font=name_font,
                fill=self.text,
                anchor="ra",
                **self._text_options(full_name),
            )
        else:
            draw.text((325, 248), name_text, font=name_font, fill=self.text)
        draw.rounded_rectangle((325, 307, 716, 354), radius=12, fill=(232, 240, 254))
        draw.text(
            (343, 330),
            "MATRICULE",
            font=self._font(12, bold=True),
            fill=self.slate,
            anchor="lm",
        )
        self._draw_mixed_matricule(draw, self.student.student_id, 435, 330, 263)

        self._draw_info_panel(
            draw,
            (325, 378, 716, 483),
            "FILIÈRE / PROGRAMME",
            program,
            self.blue,
        )
        self._draw_info_panel(
            draw,
            (735, 378, 968, 483),
            "NIVEAU",
            level,
            self.green,
        )

        draw.text(
            (325, 512),
            "RÉF. CARTE",
            font=self._font(11, bold=True),
            fill=(100, 116, 139),
        )
        reference = self._card_reference()
        draw.text((325, 535), reference, font=self._font(18, bold=True), fill=self.earth)
        self._draw_security_bars(draw, 510, 508, 185, 31, reference)

    def _draw_info_panel(self, draw, box, label, value, accent):
        draw.rounded_rectangle(box, radius=17, fill="white", outline=(226, 232, 240), width=2)
        x1, y1, x2, _ = box
        draw.rectangle((x1, y1, x1 + 7, box[3]), fill=accent)
        draw.text((x1 + 24, y1 + 20), label, font=self._font(12, bold=True), fill=self.slate)
        value_text, value_font = self._fit_font(
            draw,
            value,
            x2 - x1 - 45,
            27,
            16,
            bold=True,
        )
        if contains_arabic(value):
            draw.text(
                (x2 - 24, y1 + 58),
                value_text,
                font=value_font,
                fill=self.text,
                anchor="ra",
                **self._text_options(value),
            )
        else:
            draw.text((x1 + 24, y1 + 58), value_text, font=value_font, fill=self.text)

    def _draw_footer(self, draw):
        draw.rectangle((0, 562, self.width, self.height), fill=self.navy)
        draw.rectangle((0, 562, self.width, 568), fill=self.orange)
        draw.rectangle((0, 568, self.width, 572), fill=self.green)

        academic_year, valid_until = self._academic_period()
        draw.text((44, 592), "ANNÉE ACADÉMIQUE", font=self._font(11, bold=True), fill=(148, 163, 184))
        draw.text((44, 620), academic_year, font=self._font(20, bold=True), fill="white", anchor="lm")

        if valid_until:
            draw.text((390, 592), "VALABLE JUSQU'AU", font=self._font(11, bold=True), fill=(148, 163, 184))
            draw.text((390, 620), valid_until, font=self._font(18, bold=True), fill=(220, 252, 231), anchor="lm")

        draw.text(
            (968, 604),
            "universiter-attawoune.ml",
            font=self._font(16, bold=True),
            fill="white",
            anchor="rm",
        )
        draw.text(
            (968, 627),
            "Document universitaire nominatif",
            font=self._font(10),
            fill=(148, 163, 184),
            anchor="rm",
        )

    def _draw_shadow(self, card, box, radius):
        shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (box[0] + 5, box[1] + 8, box[2] + 5, box[3] + 8),
            radius=radius,
            fill=(15, 23, 42, 45),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        card.paste(shadow, (0, 0), shadow)

    def _draw_security_bars(self, draw, x, y, width, height, reference):
        digest = hashlib.sha256(reference.encode("utf-8")).digest()
        cursor = x
        index = 0
        while cursor < x + width:
            byte = digest[index % len(digest)]
            bar_width = 2 + (byte % 4)
            gap = 2 + ((byte >> 4) % 3)
            draw.rectangle((cursor, y, min(cursor + bar_width, x + width), y + height), fill=self.blue)
            cursor += bar_width + gap
            index += 1

    def _draw_mixed_matricule(self, draw, value, x, y, max_width):
        runs = [run.strip() for run in MIXED_ID_RUN_PATTERN.findall(str(value or "")) if run.strip()]
        separator = "  •  "
        for size in range(17, 11, -1):
            measured = []
            total_width = 0
            for run in runs:
                arabic = contains_arabic(run)
                font = self._font(size, bold=True, arabic=arabic)
                display_run = self._display_text(run)
                box = draw.textbbox((0, 0), display_run, font=font, **self._text_options(run))
                width = box[2] - box[0]
                measured.append((run, display_run, font, width))
                total_width += width
            separator_font = self._font(max(size - 2, 10), bold=True)
            separator_box = draw.textbbox((0, 0), separator, font=separator_font)
            separator_width = separator_box[2] - separator_box[0]
            total_width += separator_width * max(len(measured) - 1, 0)
            if total_width <= max_width or size == 12:
                break

        cursor = x
        for index, (run, display_run, font, width) in enumerate(measured):
            draw.text(
                (cursor, y),
                display_run,
                font=font,
                fill=self.blue,
                anchor="lm",
                **self._text_options(run),
            )
            cursor += width
            if index < len(measured) - 1:
                draw.text((cursor, y), separator, font=separator_font, fill=(100, 116, 139), anchor="lm")
                cursor += separator_width

    def _full_name(self):
        user = self.student.user
        return user.get_full_name().strip() or getattr(user, "username", "") or self.student.student_id

    def _initials(self):
        names = self._full_name().split()
        return "".join(name[0] for name in names[:2]).upper() or "ET"

    def _level_label(self):
        level = getattr(self.student, "current_level", None)
        if not level:
            return "Non renseigné"
        getter = getattr(level, "get_name_display", None)
        return getter() if callable(getter) else str(level)

    def _status_label(self):
        getter = getattr(self.student, "get_status_display", None)
        if callable(getter):
            return getter()
        labels = {
            "ACTIVE": "Actif",
            "GRADUATED": "Diplômé",
            "SUSPENDED": "Suspendu",
            "DROPPED": "Abandonné",
        }
        return labels.get(getattr(self.student, "status", "ACTIVE"), "Actif")

    def _academic_period(self):
        try:
            enrollment = self.student.enrollments.select_related("academic_year").filter(
                is_active=True,
            ).order_by("-academic_year__start_date").first()
        except (AttributeError, TypeError):
            enrollment = None

        academic_year = getattr(enrollment, "academic_year", None)
        if academic_year:
            label = academic_year.name
            end_date = academic_year.end_date.strftime("%d/%m/%Y") if academic_year.end_date else ""
            return label, end_date

        today = timezone.localdate()
        start_year = today.year if today.month >= 9 else today.year - 1
        return f"{start_year} - {start_year + 1}", ""

    def _card_reference(self):
        source = f"{self.student.student_id}:{getattr(self.student, 'enrollment_date', '')}"
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:10].upper()
        return f"UPA-{digest}"
