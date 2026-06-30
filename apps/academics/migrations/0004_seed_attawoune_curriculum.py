from datetime import date
from decimal import Decimal

from django.db import migrations


FACULTIES = [
    {
        "code": "الاسلامية",
        "name": "كلية الدراسات الاسلامية",
        "description": "مساره القرآن+ الحديث+الفقه+الحديث",
        "departments": [
            {
                "code": "الاسلامية",
                "name": "الشريعة",
                "description": "القرآن+الحديث+الفقه+العقيدة",
                "programs": [
                    {"code": "الحديث وعلومه", "name": "الدراسات الاسلامية", "duration_years": 3, "tuition_fee": "285000.00"},
                    {"code": "العقيدة", "name": "الدراسات الاسلامية", "duration_years": 3, "tuition_fee": "375000.00"},
                    {"code": "الفقه وأصوله", "name": "الدراسات الاسلامية", "duration_years": 3, "tuition_fee": "375000.00"},
                    {"code": "القرآن وعلومه", "name": "الدراسات الاسلامية", "duration_years": 3, "tuition_fee": "375000.00"},
                ],
            }
        ],
    },
    {
        "code": "التربية",
        "name": "كلية التربية والدراسات الإنسانية",
        "description": "الادارة والتخطيط+المناهج+اللغة",
        "departments": [
            {
                "code": "التربية",
                "name": "الدراسات الإنسانية",
                "description": "الادارة+المناهج+اللغة",
                "programs": [
                    {"code": "الادارة", "name": "التربية", "duration_years": 3, "tuition_fee": "450000.00"},
                    {"code": "اللغة", "name": "التربية", "duration_years": 3, "tuition_fee": "450000.00"},
                    {"code": "المناهج وطرق التدريس", "name": "التربية", "duration_years": 3, "tuition_fee": "450000.00"},
                ],
            }
        ],
    },
]

COURSE_SETS = {
    "الاسلامية": {
        "S1": [
            ("نظام الأسرة في الإسلام", "Le Systeme Familial en Islam"),
            ("الملل و النحل", "Introduction a la science des religions et de culte"),
            ("دراسات في السيرة النبوية", "Etudes sur la biographiedu Prophete"),
            ("مبادئ البحث العلمي", "Principes de la recherché Scientifique"),
            ("حفظ القرآن وتجويده(1)", "Mémoriser et reciter le coran (1)"),
            ("المهارات اللغوية(1)", "Competences Linguistique (1)"),
            ("لغة فرنسية (1)", "Français (1)"),
            ("التقنيات الحديثة في الدراسات الإسلامية والإنسانية", "Techniques modernes en études islamiques et humaines"),
            ("أصول الثقافة الإسلامية", "Origines de la culture islamique"),
            ("المدخل إلى أصول الفقه", "Introduction aux principes de la jurisprudence"),
        ],
        "S2": [
            ("المدخل إلى علوم القرآن", "Introduction aux sciences du Coran"),
            ("النظام الاقتصادي في الإسلام", "Le systeme economique en Islam"),
            ("المدخل إلى علوم الحديث", "Introduction aux sciences des Hadith"),
            ("طرائق التدريس العامة", "Methodes d’enseignment generals"),
            ("لغة فرنسية (2)", "Français(2)"),
            ("المهارات اللغوية", "Competences Linguistique(2)"),
            ("مهارات التعلم والتفكير والبحث", "Competences d’apprentissage, de reflexion et de recherché"),
            ("النظام السياسي في الإسلام", "Le systeme politique en Islam"),
            ("دراسات في التاريخ الإسلامي", "Etudes en hitoire islamique"),
            ("المدخل إلى علم العقيدة", "Introduction a la science de la croyance"),
            ("المدخل إلى الفقه الإسلامي", "Introduction a la jurisprudence Islamique"),
        ],
        "S3": [
            ("لغة فرنسية (3)", "Français(3)"),
            ("التفسير الموضوعي والتحليلي", "Interpretation objective et analytique"),
            ("أخلاقيات المهنة", "Ethique professinonnelle"),
            ("أحاديث المعاملات", "Hadith de culte"),
            ("الاستشراق والتنصير", "Orientalism et christianisation"),
            ("حفظ القرآن وتجويده (2)", "Memoriser et reciter le coran(2)"),
            ("تاريخ تدوين السنة ومناهجه", "L’histoire de la codification de la Suna et ses methods"),
            ("العقيدة الإسلامية", "Foi Islamique"),
            ("فقه العبادات (1) (الطهارة والصلاة)", "Jurisprudence du culte"),
            ("أصول التفسير", "Origine de l’intrpretation du coran"),
            ("أصول الفقه (الأدلة المختلف فيها)", "Introduction aux principes de la jurisprudence (2)"),
        ],
        "S4": [
            ("إعجاز القرآن والتفسير العلمي", "le miracle du coran l’interpretation scientifique"),
            ("أصول التخريج ودراسة الأسانيد", "Principes des Analise des Hadi"),
            ("شروح الحديث ومناهج الشراح", "L’Interpretation du Hadith et ethods des Interpretateurs"),
            ("المدخل إلى الفقه المالكي", "Introduction a la jurisprudence (Malikia)"),
            ("تفسير آيات الأحكام", "Interpretation des versets des decisions"),
            ("المنطق وأدب الخلاف والمناظرة", "logique et comportement du disaccord et du debat"),
            ("المواريث وقسمة التركات", "Heritage et partage de la succession"),
            ("مقاصد الشريعة", "Objectifs de la Loi(Chariya)"),
            ("تاريخ تدوين العقيدة ومناهجه", "L’histoire de la codification de la Foi Islamique et ses methods"),
            ("لغة فرنسية (4)", "Français(4)"),
        ],
        "S5": [
            ("مصادر العقيدة", "Études sur les sources de la croyance"),
            ("مصادر السنة", "Études des sources prophétiques"),
            ("أحاديث الأطعمة و الأشربة", "Hadiths sur les nourritures et boissons"),
            ("فقه العبادات(2)", "Jurisprudence de l’adoration"),
            ("كتب الضعفاء و الموضوعات", "Livres des hadiths douteux et mentis"),
            ("مصادر التفسير", "Études sur les sources de l'exégèse"),
            ("حاضر العالم الإسلامي", "Histoire contemporaine du monde islamique"),
            ("القواعد الفقهية", "Regle de la Jurisprudence"),
            ("الدعوة و الإعلام", "Prédication et médias"),
            ("الفرنسية(5)", "Français (5)"),
            ("مادة التخصص", "Matière d’spécialisation"),
        ],
        "S6": [
            ("اللغة الفرنسية(6)", "Français (6)"),
            ("السياسة الشرعية", "Politique islamique"),
            ("تاريخ و حضارة مالي", "Histoire et civilisation du Mali"),
            ("فقه النوازل", "Jurisprudence des actes inédits"),
            ("قواعد التفسير و الترجيح", "Règles de l’exégèse et de la prédilection"),
            ("منهج أهل في تقرير العقيدة", "Méthodologie d'explication utile de la croyance"),
            ("دراسات معمقة في علوم الحديث", "Études approfondies en sciences des hadiths"),
        ],
    },
    "التربية": {
        "S1": [
            ("نظام الأسرة في الإسلام", "Le système familial en l’islam"),
            ("المدخل إلى التربية الخاصة", "L’introduction à l’éducation spéciale"),
            ("مقدمة في التعلم و التعليم", "Avant propos de l’apprentissage et l’enseignement"),
            ("مبادئ البحث العلمي", "Les principaux de la recherche scientifique"),
            ("حفظ القرآن وتجويده (1)", "Mémorisation et bonne lecture du Coran"),
            ("لغة عربية (1)", "LV1 arabe"),
            ("الفرنسية(1)", "LV1 français"),
            ("التقنيات الحديثة في الدراسات الإسلامية والإنسانية", "Les techniques modernes aux études islamiques et humaines"),
            ("أصول الثقافة الإسلامية", "Les fondamentaux de la culture islamique"),
            ("أصول التربية الإسلامية", "Les fondamentaux de l’education"),
        ],
        "S2": [
            ("مهارات الاتصال", "Les savoirs faire de la communication"),
            ("المدخل إلى التقويم التربوي", "L’introduction à l’évaluation pédagogique"),
            ("النظام الاقتصادي في الإسلام", "Le système économique en islam"),
            ("طرائق التدريس العامة", "Les pédagogies générales"),
            ("لغة فرنسية (2)", "LV2 français"),
            ("علم النفس التربوي", "La psychologie éducative"),
            ("المدخل إلى الإرشاد و التوجيه التربوي", "Introduction à l’orientation éducative"),
            ("مهارات التعلم والتفكير والبحث", "Les savoirs faire de l’apprentissage, réflexion et recherche"),
            ("النظام السياسي في الإسلام", "Le système politique en l’islam"),
            ("المدخل للقيادة التربوية", "Introduction à l’éducation approfondie"),
            ("لغة عربية (2)", "LV2 arabe"),
        ],
        "S3": [
            ("لغة فرنسية (3)", "LV3 français"),
            ("المدخل إلى الأدبالعربي", "Introduction à l’littérature arabe"),
            ("أخلاقيات المهنة", "La déontologie professionnelle"),
            ("دراسات في علم البلاغة", '"Études en science de la rhétorique"'),
            ("الاستشراق و التنصر", "L’orientalisme et la christianisation"),
            ("علم النفس النمو", "Psychologie de croissance"),
            ("إعداد المعلم و تطويره", "Formation de l’enseignement et son évolution"),
            ("العقيدة الإسلامية", "La croyance islamique"),
            ("فقه العبادات (1) (الطهارة والصلاة)", "Jurisprudence des adorations (la propreté et prière)"),
            ("التحرير العربي", "La rédaction arabe"),
            ("التحضير و إدارة الصف", "La préparation et gestion de classe"),
        ],
        "S4": [
            ("إعجاز القرآن والتفسير العلمي", '"L\'inimitabilité du Coran et l\'interprétation scientifique'),
            ("المناهج المدرسية", "Les méthodes pédagogiques"),
            ("العروض و القافية", "L'Art du Vers et de la Rime"),
            ("تاريخ التربية و تطور الفكر", "L’histoire de l’éducation et évolution de pensée"),
            ("مصادر اللغة و الأدب", "Sources de la langue et littérature"),
            ("إدارة المؤسسات التربوية", "Gestion des établissements éducatifs"),
            ("مقاصد الشريعة", "Les objectifs de la charia"),
            ("الوسائل التعليمية", "Les moyens pédagogiques"),
            ("اللسانيات", "Linguistiques"),
            ("لغة فرنسية (4)", "LV4 français"),
        ],
        "S5": [
            ("استخدام الحاسوب", "Formation informatique"),
            ("الفكر التربوي", "Pensée éducative"),
            ("فقه العبادات(2)", "Jurisprudence des adorations 2"),
            ("بناء السلوك", "Formation de conduite"),
            ("استراتيجيات التدريس الفعال", "Pédagogies efficaces"),
            ("دراسات معمفة في الأدب", "Études approfondies en littérature"),
            ("فقه اللغة", "Compréhension de la langue"),
            ("حاضر العالم الإسلامي", "Le monde islamique contemporain"),
            ("النقد الأدبي", "La critique littéraire"),
            ("الفرنسية(5)", "Français( 5)"),
            ("الإدارة و التخطيط التربوي", "Administration et Planification"),
        ],
        "S6": [
            ("الفرنسية(6)", "Français (6)"),
            ("السياسة الشرعية", "Politique islamique"),
            ("تاريخ و حضارة مالي", "Histoire et civilisation du Mali"),
            ("دراسات في علم اللغة", "Études des sciences linguistiques"),
            ("التربية الإعلامية", "Éducation médiathèque"),
            ("النصوص الأدبية", "Textes littéraires"),
            ("مواد التخصص", "Matières de spécialisation"),
        ],
    },
}

SEMESTER_TO_LEVEL = {
    "S1": ("L1", "S1"),
    "S2": ("L1", "S2"),
    "S3": ("L2", "S1"),
    "S4": ("L2", "S2"),
    "S5": ("L3", "S1"),
    "S6": ("L3", "S2"),
}


def update_fields(instance, **fields):
    changed = False
    for field, value in fields.items():
        if getattr(instance, field) != value:
            setattr(instance, field, value)
            changed = True
    if changed:
        instance.save(update_fields=list(fields.keys()))


def get_or_update_course(Course, code, program, level, semester_type, name, description):
    course = Course.objects.filter(code=code).first()
    if course is None:
        course = Course.objects.filter(
            program=program,
            level=level,
            semester_type=semester_type,
            name=name,
        ).first()

    values = {
        "name": name,
        "program": program,
        "course_type": "REQUIRED",
        "credits": 1,
        "hours_lecture": 30,
        "hours_practical": 0,
        "hours_tutorial": 0,
        "description": description,
        "semester_type": semester_type,
        "level": level,
        "coefficient": Decimal("1.0"),
        "is_active": True,
    }

    if course is None:
        Course.objects.create(code=code, **values)
        return

    if not Course.objects.filter(code=code).exclude(pk=course.pk).exists():
        course.code = code
    for field, value in values.items():
        setattr(course, field, value)
    course.save()


def seed_attawoune_curriculum(apps, schema_editor):
    AcademicYear = apps.get_model("university", "AcademicYear")
    Semester = apps.get_model("university", "Semester")
    Faculty = apps.get_model("university", "Faculty")
    Department = apps.get_model("university", "Department")
    Level = apps.get_model("university", "Level")
    Program = apps.get_model("university", "Program")
    Course = apps.get_model("academics", "Course")

    levels = {}
    for name, order in [("L1", 1), ("L2", 2), ("L3", 3)]:
        level, _ = Level.objects.get_or_create(name=name, defaults={"order": order})
        update_fields(level, order=order)
        levels[name] = level

    academic_year = AcademicYear.objects.filter(is_current=True).first()
    if academic_year is None:
        academic_year, _ = AcademicYear.objects.get_or_create(
            name="2025 - 2026",
            defaults={
                "start_date": date(2025, 10, 6),
                "end_date": date(2026, 9, 10),
                "is_current": True,
            },
        )
    update_fields(
        academic_year,
        start_date=getattr(academic_year, "start_date", date(2025, 10, 6)) or date(2025, 10, 6),
        end_date=getattr(academic_year, "end_date", date(2026, 9, 10)) or date(2026, 9, 10),
        is_current=True,
    )
    AcademicYear.objects.filter(is_current=True).exclude(pk=academic_year.pk).update(is_current=False)

    Semester.objects.get_or_create(
        academic_year=academic_year,
        semester_type="S1",
        defaults={"start_date": date(2025, 10, 6), "end_date": date(2026, 1, 31), "is_current": True},
    )
    Semester.objects.get_or_create(
        academic_year=academic_year,
        semester_type="S2",
        defaults={"start_date": date(2026, 2, 1), "end_date": date(2026, 6, 30), "is_current": False},
    )

    programs_by_faculty = {}
    for faculty_data in FACULTIES:
        faculty, _ = Faculty.objects.get_or_create(
            code=faculty_data["code"],
            defaults={"name": faculty_data["name"], "description": faculty_data["description"]},
        )
        update_fields(faculty, name=faculty_data["name"], description=faculty_data["description"])
        programs_by_faculty[faculty.code] = []

        for department_data in faculty_data["departments"]:
            department, _ = Department.objects.get_or_create(
                code=department_data["code"],
                defaults={
                    "name": department_data["name"],
                    "description": department_data["description"],
                    "faculty": faculty,
                },
            )
            update_fields(
                department,
                name=department_data["name"],
                description=department_data["description"],
                faculty=faculty,
            )

            for program_data in department_data["programs"]:
                program, _ = Program.objects.get_or_create(
                    code=program_data["code"],
                    defaults={
                        "name": program_data["name"],
                        "department": department,
                        "duration_years": program_data["duration_years"],
                        "tuition_fee": Decimal(program_data["tuition_fee"]),
                        "description": "",
                        "is_active": True,
                    },
                )
                update_fields(
                    program,
                    name=program_data["name"],
                    department=department,
                    duration_years=program_data["duration_years"],
                    tuition_fee=Decimal(program_data["tuition_fee"]),
                    is_active=True,
                )
                program.levels.set([levels["L1"], levels["L2"], levels["L3"]])
                programs_by_faculty[faculty.code].append(program)

    for faculty_code, programs in programs_by_faculty.items():
        for program in programs:
            for curriculum_semester, courses in COURSE_SETS[faculty_code].items():
                level_name, semester_type = SEMESTER_TO_LEVEL[curriculum_semester]
                level = levels[level_name]
                for index, (name, description) in enumerate(courses, start=1):
                    code = f"P{program.pk}-{curriculum_semester}-{index:02d}"
                    get_or_update_course(Course, code, program, level, semester_type, name, description)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("university", "0003_programfee"),
        ("academics", "0003_alter_course_options_remove_course_semester_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_attawoune_curriculum, noop_reverse),
    ]
