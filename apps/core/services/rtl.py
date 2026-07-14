import re
import unicodedata


ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")
LTR_RUN_PATTERN = re.compile(r"[A-Za-z0-9À-ÿ/.,+\-]+")
YEAR_RANGE_PATTERN = re.compile(r"(\d{4})\s*-\s*(\d{4})")


def _arabic_forms():
    forms = {}
    for start, end in ((0xFB50, 0xFDFF), (0xFE70, 0xFEFF)):
        for codepoint in range(start, end + 1):
            character = chr(codepoint)
            decomposition = unicodedata.decomposition(character).split()
            if len(decomposition) != 2 or not decomposition[0].startswith("<"):
                continue
            form = decomposition[0].strip("<>")
            if form not in {"isolated", "final", "initial", "medial"}:
                continue
            try:
                base = chr(int(decomposition[1], 16))
            except ValueError:
                continue
            forms.setdefault(base, {})[form] = character
    return forms


ARABIC_FORMS = _arabic_forms()


def contains_arabic(value):
    return bool(ARABIC_PATTERN.search(str(value or "")))


def shape_arabic(value):
    text = str(value or "").strip()
    if not text:
        return ""
    shaped_lines = []
    for line in text.splitlines() or [text]:
        units = []
        for character in line:
            if unicodedata.combining(character) and units:
                units[-1] += character
            else:
                units.append(character)

        shaped_units = []
        for index, unit in enumerate(units):
            character = unit[0]
            forms = ARABIC_FORMS.get(character)
            if not forms:
                shaped_units.append(unit)
                continue

            previous = units[index - 1][0] if index > 0 else ""
            following = units[index + 1][0] if index + 1 < len(units) else ""
            previous_forms = ARABIC_FORMS.get(previous, {})
            following_forms = ARABIC_FORMS.get(following, {})
            joins_previous = bool(
                previous_forms.get("initial") or previous_forms.get("medial")
            ) and bool(forms.get("final") or forms.get("medial"))
            joins_following = bool(
                forms.get("initial") or forms.get("medial")
            ) and bool(following_forms.get("final") or following_forms.get("medial"))

            if joins_previous and joins_following and forms.get("medial"):
                shaped = forms["medial"]
            elif joins_previous and forms.get("final"):
                shaped = forms["final"]
            elif joins_following and forms.get("initial"):
                shaped = forms["initial"]
            else:
                shaped = forms.get("isolated", character)
            shaped_units.append(shaped + unit[1:])

        visual = "".join(reversed(shaped_units))
        visual = LTR_RUN_PATTERN.sub(lambda match: match.group(0)[::-1], visual)
        visual = YEAR_RANGE_PATTERN.sub(
            lambda match: f"{match.group(2)} - {match.group(1)}",
            visual,
        )
        visual = visual.translate(str.maketrans("()[]{}", ")(][}{"))
        shaped_lines.append(visual)
    return "\n".join(shaped_lines)
