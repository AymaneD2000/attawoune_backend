import io
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .rtl import contains_arabic as _contains_arabic
from .rtl import shape_arabic as _shape_arabic


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "bulletin"
HEADER_IMAGE = ASSET_DIR / "header.jpeg"
FOOTER_IMAGE = ASSET_DIR / "footer.jpeg"
FONT_DIR = ASSET_DIR / "fonts"

PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - (24 * mm)
FRENCH_COLUMN_WIDTH = CONTENT_WIDTH * 0.517
SCORE_COLUMN_WIDTH = CONTENT_WIDTH * 0.174
ARABIC_COLUMN_WIDTH = CONTENT_WIDTH - FRENCH_COLUMN_WIDTH - SCORE_COLUMN_WIDTH

PALE_BLUE = colors.HexColor("#AFC4E4")

FONT_LATIN = "BulletinLatin"
FONT_LATIN_BOLD = "BulletinLatinBold"
FONT_ARABIC = "BulletinArabic"
FONT_ARABIC_BOLD = "BulletinArabicBold"

LEVEL_TITLES = {
    "L1": ("PREMIÈRE ANNÉE", "السنة الأولى"),
    "L2": ("DEUXIÈME ANNÉE", "السنة الثانية"),
    "L3": ("TROISIÈME ANNÉE", "السنة الثالثة"),
    "M1": ("MASTER 1", "السنة الأولى ماستر"),
    "M2": ("MASTER 2", "السنة الثانية ماستر"),
    "D1": ("DOCTORAT 1", "السنة الأولى دكتوراه"),
    "D2": ("DOCTORAT 2", "السنة الثانية دكتوراه"),
    "D3": ("DOCTORAT 3", "السنة الثالثة دكتوراه"),
}

PROGRAM_NAMES_FR = {
    "العقيدة": "Théologie",
    "الفقه وأصوله": "Jurisprudence",
    "القرآن وعلومه": "Coran et sciences coraniques",
    "الحديث وعلومه": "Hadith et sciences du Hadith",
    "الادارة": "Administration et planification",
    "اللغة": "Langue arabe",
    "المناهج وطرق التدريس": "Curriculum et méthodes d'enseignement",
}


def _register_fonts():
    fonts = {
        FONT_LATIN: FONT_DIR / "DejaVuSerif.ttf",
        FONT_LATIN_BOLD: FONT_DIR / "DejaVuSerif-Bold.ttf",
        FONT_ARABIC: FONT_DIR / "NotoNaskhArabic-Regular.ttf",
        FONT_ARABIC_BOLD: FONT_DIR / "NotoNaskhArabic-Bold.ttf",
    }
    registered = set(pdfmetrics.getRegisteredFontNames())
    for name, path in fonts.items():
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, str(path)))


def _format_score(value):
    number = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    formatted = f"{number:.2f}".rstrip("0").rstrip(".")
    return formatted.replace(".", ",")


def _course_labels(course):
    values = [str(course.name or "").strip(), str(course.description or "").strip()]
    arabic = next((value for value in values if value and _contains_arabic(value)), "")
    french = next((value for value in values if value and not _contains_arabic(value)), "")
    if not french:
        french = str(course.code or values[0] or "Matière")
    if not arabic:
        arabic = str(course.name or "") if _contains_arabic(course.name) else ""
    return french, arabic


def _faculty_names(student):
    faculty = student.program.department.faculty
    faculty_name = str(faculty.name or "").strip()
    faculty_code = str(faculty.code or "").strip()
    source = f"{faculty_name} {faculty_code}"
    if "الاسلام" in source or "الإسلام" in source:
        french = "Faculté des Études Islamiques"
    elif "التربية" in source or "الإنسانية" in source:
        french = "Faculté de l'Éducation et des Études Humaines"
    else:
        french = faculty_name if not _contains_arabic(faculty_name) else "Université Privée Attawoune"
    arabic = faculty_name if _contains_arabic(faculty_name) else ""
    return french, arabic


def _program_names(student):
    program = student.program
    program_code = str(program.code or "").strip()
    program_name = str(program.name or "").strip()
    french = PROGRAM_NAMES_FR.get(program_code)
    if not french:
        french = program_name if not _contains_arabic(program_name) else program_code
    arabic = program_code if _contains_arabic(program_code) else program_name
    return french, arabic


def _wrap_arabic(value, max_width, font_name, font_size):
    words = str(value or "").split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if pdfmetrics.stringWidth(_shape_arabic(candidate), font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return [_shape_arabic(line) for line in lines]


def _arabic_paragraph(value, style, max_width=None):
    if max_width:
        lines = []
        for source_line in str(value or "").splitlines():
            lines.extend(_wrap_arabic(source_line, max_width, style.fontName, style.fontSize))
        text = "<br/>".join(escape(line) for line in lines)
    else:
        text = escape(_shape_arabic(value))
    return Paragraph(text or " ", style)


def _styles():
    return {
        "faculty_fr": ParagraphStyle(
            "BulletinFacultyFr",
            fontName=FONT_LATIN_BOLD,
            fontSize=8.5,
            leading=10,
            alignment=TA_LEFT,
        ),
        "faculty_ar": ParagraphStyle(
            "BulletinFacultyAr",
            fontName=FONT_ARABIC_BOLD,
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
        ),
        "title_fr": ParagraphStyle(
            "BulletinTitleFr",
            fontName=FONT_LATIN_BOLD,
            fontSize=14.5,
            leading=16.5,
            alignment=TA_CENTER,
        ),
        "title_ar": ParagraphStyle(
            "BulletinTitleAr",
            fontName=FONT_ARABIC_BOLD,
            fontSize=18,
            leading=20,
            alignment=TA_CENTER,
        ),
        "identity_fr": ParagraphStyle(
            "BulletinIdentityFr",
            fontName=FONT_LATIN_BOLD,
            fontSize=10.5,
            leading=15,
            alignment=TA_LEFT,
        ),
        "identity_ar": ParagraphStyle(
            "BulletinIdentityAr",
            fontName=FONT_ARABIC_BOLD,
            fontSize=12,
            leading=17,
            alignment=TA_RIGHT,
        ),
        "header_fr": ParagraphStyle(
            "BulletinHeaderFr",
            fontName=FONT_LATIN_BOLD,
            fontSize=14,
            leading=16,
            alignment=TA_CENTER,
        ),
        "header_score": ParagraphStyle(
            "BulletinHeaderScore",
            fontName=FONT_LATIN_BOLD,
            fontSize=11,
            leading=12,
            alignment=TA_CENTER,
        ),
        "course_fr": ParagraphStyle(
            "BulletinCourseFr",
            fontName=FONT_LATIN,
            fontSize=8.2,
            leading=9.8,
            alignment=TA_LEFT,
        ),
        "course_ar": ParagraphStyle(
            "BulletinCourseAr",
            fontName=FONT_ARABIC,
            fontSize=11.5,
            leading=13,
            alignment=TA_RIGHT,
        ),
        "score": ParagraphStyle(
            "BulletinScore",
            fontName=FONT_LATIN_BOLD,
            fontSize=13.5,
            leading=15,
            alignment=TA_CENTER,
        ),
        "total_fr": ParagraphStyle(
            "BulletinTotalFr",
            fontName=FONT_LATIN_BOLD,
            fontSize=11.5,
            leading=14,
            alignment=TA_LEFT,
        ),
        "total_ar": ParagraphStyle(
            "BulletinTotalAr",
            fontName=FONT_ARABIC_BOLD,
            fontSize=14,
            leading=16,
            alignment=TA_RIGHT,
        ),
        "average": ParagraphStyle(
            "BulletinAverage",
            fontName=FONT_LATIN_BOLD,
            fontSize=16,
            leading=18,
            alignment=TA_CENTER,
        ),
    }


def _page_artwork(canvas, document):
    canvas.saveState()
    canvas.setTitle(getattr(document, "title", "Bulletin de notes"))
    artwork_width = PAGE_WIDTH - (4 * mm)
    header_height = artwork_width * 171 / 986
    footer_height = artwork_width * 84 / 986
    canvas.drawImage(
        str(HEADER_IMAGE),
        2 * mm,
        PAGE_HEIGHT - header_height - (2 * mm),
        width=artwork_width,
        height=header_height,
        preserveAspectRatio=True,
        mask="auto",
    )
    canvas.drawImage(
        str(FOOTER_IMAGE),
        2 * mm,
        2 * mm,
        width=artwork_width,
        height=footer_height,
        preserveAspectRatio=True,
        mask="auto",
    )
    canvas.restoreState()


def _identity_elements(report_card, styles):
    student = report_card.student
    user = student.user
    full_name = user.get_full_name().strip() or user.username
    faculty_fr, faculty_ar = _faculty_names(student)
    program_fr, program_ar = _program_names(student)
    level_code = getattr(student.current_level, "name", "")
    level_fr, level_ar = LEVEL_TITLES.get(
        level_code,
        (str(student.current_level or ""), str(student.current_level or "")),
    )
    academic_year = report_card.semester.academic_year.name

    faculty_table = Table(
        [[
            Paragraph(
                f"{escape(faculty_fr)}  Année Universitaire {escape(academic_year)}",
                styles["faculty_fr"],
            ),
            _arabic_paragraph(
                f"{faculty_ar} العام الجامعي {academic_year}",
                styles["faculty_ar"],
            ),
        ]],
        colWidths=[CONTENT_WIDTH * 0.58, CONTENT_WIDTH * 0.42],
    )
    faculty_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    title_table = Table(
        [[
            Paragraph(f"RELEVÉS DE NOTES DE LA<br/>{escape(level_fr)}", styles["title_fr"]),
            _arabic_paragraph(f"كشف الدرجات {level_ar}", styles["title_ar"]),
        ]],
        colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
    )
    title_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    if _contains_arabic(full_name):
        french_block_name = (
            f'<font name="{FONT_ARABIC_BOLD}">{escape(_shape_arabic(full_name))}</font>'
        )
    else:
        french_block_name = escape(full_name)

    identity_table = Table(
        [[
            Paragraph(
                f"Prénoms et Nom : {french_block_name}<br/>Filière : {escape(program_fr)}",
                styles["identity_fr"],
            ),
            _arabic_paragraph(
                f"الاسم الكامل: {full_name}\nالمسار: {program_ar}",
                styles["identity_ar"],
                max_width=(CONTENT_WIDTH / 2) - 8,
            ),
        ]],
        colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
    )
    identity_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [faculty_table, title_table, identity_table, Spacer(1, 3 * mm)]


def _selected_semesters(report_card):
    from apps.academics.models import ReportCard

    if not report_card.is_published:
        return [report_card.semester]

    report_cards = ReportCard.objects.filter(
        student=report_card.student,
        semester__academic_year=report_card.semester.academic_year,
        is_published=True,
    ).select_related("semester").order_by("semester__semester_type")
    semesters = [card.semester for card in report_cards]
    if report_card.semester_id not in {semester.id for semester in semesters}:
        semesters.append(report_card.semester)
    return sorted(semesters, key=lambda semester: semester.semester_type)


def _course_grades(report_card, semesters):
    from apps.academics.models import CourseGrade

    queryset = CourseGrade.objects.filter(
        student=report_card.student,
        semester__in=semesters,
    ).select_related("course", "semester").order_by("semester__semester_type", "course__code")
    if report_card.is_published:
        queryset = queryset.filter(is_validated=True)
    return list(queryset)


def _grades_table(course_grades, styles):
    rows = [[
        Paragraph("Matières", styles["header_fr"]),
        Paragraph(
            f'<font name="{FONT_ARABIC_BOLD}">{escape(_shape_arabic("الدرجة /20"))}</font>'
            f'<br/><font name="{FONT_LATIN_BOLD}">Notes/20</font>',
            styles["header_score"],
        ),
        "",
    ]]

    if course_grades:
        for course_grade in course_grades:
            french, arabic = _course_labels(course_grade.course)
            rows.append([
                Paragraph(escape(french), styles["course_fr"]),
                Paragraph(_format_score(course_grade.final_score), styles["score"]),
                _arabic_paragraph(
                    arabic,
                    styles["course_ar"],
                    max_width=float(ARABIC_COLUMN_WIDTH) - 8,
                ),
            ])
        total = sum((grade.final_score for grade in course_grades), Decimal("0"))
    else:
        rows.append([
            Paragraph("Aucune note disponible", styles["course_fr"]),
            Paragraph("-", styles["score"]),
            _arabic_paragraph("لا توجد درجات", styles["course_ar"]),
        ])
        total = Decimal("0")

    rows.append([
        Paragraph("Total", styles["total_fr"]),
        Paragraph(_format_score(total), styles["average"]),
        _arabic_paragraph("المجموع", styles["total_ar"]),
    ])

    table = LongTable(
        rows,
        colWidths=[
            float(FRENCH_COLUMN_WIDTH),
            float(SCORE_COLUMN_WIDTH),
            float(ARABIC_COLUMN_WIDTH),
        ],
        repeatRows=1,
        splitByRow=1,
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE_BLUE),
        ("BACKGROUND", (1, -1), (1, -1), PALE_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.65, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 1), (-1, -2), 2.5),
        ("BOTTOMPADDING", (0, 1), (-1, -2), 2.5),
        ("TOPPADDING", (0, -1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 3),
    ]))
    return table


def _average_table(course_grades, report_card, styles):
    weighted_total = Decimal("0")
    total_credits = 0
    for course_grade in course_grades:
        credits = course_grade.course.credits or 0
        weighted_total += course_grade.final_score * credits
        total_credits += credits
    average = weighted_total / total_credits if total_credits else report_card.gpa

    table = Table(
        [[
            Paragraph("Moyenne", styles["total_fr"]),
            Paragraph(_format_score(average), styles["average"]),
            _arabic_paragraph("المعدل", styles["total_ar"]),
        ]],
        colWidths=[
            float(FRENCH_COLUMN_WIDTH),
            float(SCORE_COLUMN_WIDTH),
            float(ARABIC_COLUMN_WIDTH),
        ],
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), PALE_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.65, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def generate_bulletin_pdf(report_card):
    _register_fonts()
    styles = _styles()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=38 * mm,
        bottomMargin=20 * mm,
        title=f"Bulletin {report_card.student.student_id}",
        author="Université Privée Attawoune",
        subject="Relevé de notes bilingue",
    )

    semesters = _selected_semesters(report_card)
    all_course_grades = _course_grades(report_card, semesters)
    grades_by_semester = {
        semester.id: [grade for grade in all_course_grades if grade.semester_id == semester.id]
        for semester in semesters
    }

    elements = _identity_elements(report_card, styles)
    for index, semester in enumerate(semesters):
        if index:
            elements.append(Spacer(1, 2.5 * mm))
        elements.append(_grades_table(grades_by_semester.get(semester.id, []), styles))
    elements.extend([
        Spacer(1, 4 * mm),
        _average_table(all_course_grades, report_card, styles),
    ])

    document.build(elements, onFirstPage=_page_artwork, onLaterPages=_page_artwork)
    buffer.seek(0)
    return buffer
