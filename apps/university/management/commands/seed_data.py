"""
Django management command to populate the database with realistic
Malian university data for comprehensive testing.

Usage: python manage.py seed_data
"""
import random
from decimal import Decimal
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


# =========================================================================
# DATA CONSTANTS
# =========================================================================

MALE_FIRST_NAMES = [
    'Amadou', 'Moussa', 'Ibrahim', 'Oumar', 'Mamadou', 'Modibo',
    'Seydou', 'Boubacar', 'Abdoulaye', 'Souleymane', 'Bakary', 'Cheick',
    'Drissa', 'Ousmane', 'Adama', 'Lassine', 'Youssouf', 'Hamidou',
    'Issa', 'Kalilou', 'Mohamed', 'Sidy', 'Tiécoura', 'Daouda',
    'Mahamadou', 'Karim', 'Sékou', 'Baba', 'Nouhoum', 'Alassane',
]

FEMALE_FIRST_NAMES = [
    'Fatoumata', 'Aminata', 'Mariam', 'Kadiatou', 'Aïssata', 'Rokia',
    'Oumou', 'Bintou', 'Awa', 'Djénéba', 'Safiatou', 'Hawa',
    'Assitan', 'Fanta', 'Nana', 'Sira', 'Korotoumou', 'Salimata',
    'Maimouna', 'Ramata', 'Kadia', 'Tenin', 'Dado', 'Niakalé',
    'Djeneba', 'Mah', 'Sanata', 'Nassira', 'Souadou', 'Astan',
]

LAST_NAMES = [
    'Traoré', 'Coulibaly', 'Diarra', 'Keïta', 'Konaté', 'Sidibé',
    'Sangaré', 'Touré', 'Cissé', 'Diallo', 'Camara', 'Samaké',
    'Dembélé', 'Kouyaté', 'Sissoko', 'Maïga', 'Bah', 'Sylla',
    'Doumbia', 'Fané', 'Kanté', 'Bagayoko', 'Sacko', 'Togola',
    'Diakité', 'Koné', 'Niaré', 'Haidara', 'Diabaté', 'Guindo',
]

FACULTIES = [
    {
        'name': 'Faculté des Sciences et Technologies',
        'code': 'FST',
        'description': "Faculté regroupant les formations en sciences exactes, informatique et technologies.",
        'departments': [
            {
                'name': 'Département Informatique',
                'code': 'INFO',
                'description': "Formation en informatique, programmation et systèmes d'information.",
                'program': {
                    'name': 'Licence Informatique',
                    'code': 'LIC-INFO',
                    'description': 'Formation complète en informatique et développement logiciel.',
                    'tuition_fee': 250000,
                    'duration_years': 3,
                },
                # (name, code, credits, hours_lecture, hours_tutorial, hours_practical)
                'courses_s1': [
                    ('Algorithmique et Structures de Données', 'INFO101', 6, 30, 15, 10),
                    ('Programmation Python', 'INFO102', 4, 25, 10, 15),
                    ('Mathématiques pour Informatique', 'INFO103', 5, 30, 15, 0),
                    ('Architecture des Ordinateurs', 'INFO104', 4, 25, 10, 10),
                    ('Anglais Scientifique', 'INFO105', 2, 20, 0, 0),
                ],
                'courses_s2': [
                    ('Bases de Données', 'INFO201', 6, 30, 15, 10),
                    ('Programmation Web', 'INFO202', 5, 25, 10, 15),
                    ('Réseaux Informatiques', 'INFO203', 4, 25, 15, 10),
                    ('Systèmes d\'Exploitation', 'INFO204', 4, 25, 10, 10),
                    ('Probabilités et Statistiques', 'INFO205', 3, 25, 10, 0),
                ],
            },
            {
                'name': 'Département Mathématiques-Physique',
                'code': 'MATHPHY',
                'description': 'Formation en mathématiques fondamentales et physique.',
                'program': {
                    'name': 'Licence Mathématiques-Physique',
                    'code': 'LIC-MP',
                    'description': 'Formation en mathématiques et physique fondamentales.',
                    'tuition_fee': 200000,
                    'duration_years': 3,
                },
                'courses_s1': [
                    ('Analyse Mathématique I', 'MATH101', 6, 30, 15, 0),
                    ('Algèbre Linéaire', 'MATH102', 5, 30, 15, 0),
                    ('Mécanique Générale', 'PHY101', 5, 25, 10, 10),
                    ('Chimie Générale', 'PHY102', 4, 25, 10, 10),
                    ('Méthodologie du Travail Universitaire', 'MTU101', 2, 20, 0, 0),
                ],
                'courses_s2': [
                    ('Analyse Mathématique II', 'MATH201', 6, 30, 15, 0),
                    ('Algèbre II', 'MATH202', 5, 30, 15, 0),
                    ('Électromagnétisme', 'PHY201', 5, 25, 10, 10),
                    ('Optique Géométrique', 'PHY202', 4, 25, 10, 10),
                    ('Informatique Générale', 'MTU201', 2, 20, 0, 10),
                ],
            },
        ],
    },
    {
        'name': 'Faculté des Lettres et Sciences du Langage',
        'code': 'FLSL',
        'description': "Faculté dédiée aux études littéraires, linguistiques et culturelles.",
        'departments': [
            {
                'name': 'Département Lettres Modernes',
                'code': 'LETMOD',
                'description': 'Formation en littérature française et africaine.',
                'program': {
                    'name': 'Licence Lettres Modernes',
                    'code': 'LIC-LM',
                    'description': 'Formation en littérature, linguistique et culture.',
                    'tuition_fee': 180000,
                    'duration_years': 3,
                },
                'courses_s1': [
                    ('Littérature Française du XIXe siècle', 'LET101', 5, 30, 15, 0),
                    ('Grammaire Française', 'LET102', 4, 25, 15, 0),
                    ('Introduction à la Linguistique', 'LET103', 4, 25, 10, 0),
                    ('Littérature Africaine Francophone', 'LET104', 5, 30, 15, 0),
                    ('Techniques d\'Expression Écrite', 'LET105', 2, 20, 10, 0),
                ],
                'courses_s2': [
                    ('Littérature Française du XXe siècle', 'LET201', 5, 30, 15, 0),
                    ('Phonétique et Phonologie', 'LET202', 4, 25, 10, 0),
                    ('Sociolinguistique', 'LET203', 4, 25, 10, 0),
                    ('Littérature Orale Africaine', 'LET204', 5, 30, 15, 0),
                    ('Anglais Littéraire', 'LET205', 2, 20, 10, 0),
                ],
            },
            {
                'name': 'Département Sciences de l\'Éducation',
                'code': 'SCEDU',
                'description': "Formation en pédagogie et sciences de l'éducation.",
                'program': {
                    'name': 'Licence Sciences de l\'Éducation',
                    'code': 'LIC-SE',
                    'description': "Formation en pédagogie, didactique et gestion de l'éducation.",
                    'tuition_fee': 180000,
                    'duration_years': 3,
                },
                'courses_s1': [
                    ('Psychologie de l\'Éducation', 'EDU101', 5, 25, 15, 0),
                    ('Sociologie de l\'Éducation', 'EDU102', 4, 25, 10, 0),
                    ('Histoire de l\'Éducation au Mali', 'EDU103', 4, 25, 10, 0),
                    ('Didactique Générale', 'EDU104', 5, 25, 15, 0),
                    ('Statistiques Appliquées', 'EDU105', 2, 20, 10, 0),
                ],
                'courses_s2': [
                    ('Pédagogie Active', 'EDU201', 5, 25, 15, 0),
                    ('Évaluation des Apprentissages', 'EDU202', 4, 25, 10, 0),
                    ('Gestion des Systèmes Éducatifs', 'EDU203', 4, 25, 10, 0),
                    ('Ingénierie de Formation', 'EDU204', 5, 25, 15, 0),
                    ('Stage d\'Observation', 'EDU205', 2, 0, 0, 40),
                ],
            },
        ],
    },
    {
        'name': 'Faculté des Sciences Économiques et de Gestion',
        'code': 'FSEG',
        'description': "Faculté des formations en économie, gestion et commerce.",
        'departments': [
            {
                'name': 'Département Sciences Économiques',
                'code': 'ECON',
                'description': "Formation en théorie économique et analyse.",
                'program': {
                    'name': 'Licence Sciences Économiques',
                    'code': 'LIC-ECO',
                    'description': 'Formation en micro et macroéconomie, politique économique.',
                    'tuition_fee': 220000,
                    'duration_years': 3,
                },
                'courses_s1': [
                    ('Microéconomie I', 'ECO101', 6, 30, 15, 0),
                    ('Macroéconomie I', 'ECO102', 5, 30, 15, 0),
                    ('Mathématiques pour Économistes', 'ECO103', 5, 30, 15, 0),
                    ('Introduction au Droit', 'ECO104', 3, 25, 10, 0),
                    ('Comptabilité Générale', 'ECO105', 3, 25, 10, 0),
                ],
                'courses_s2': [
                    ('Microéconomie II', 'ECO201', 6, 30, 15, 0),
                    ('Macroéconomie II', 'ECO202', 5, 30, 15, 0),
                    ('Statistiques Économiques', 'ECO203', 5, 30, 15, 0),
                    ('Économie du Développement', 'ECO204', 4, 25, 10, 0),
                    ('Finances Publiques', 'ECO205', 2, 20, 10, 0),
                ],
            },
            {
                'name': 'Département Gestion',
                'code': 'GEST',
                'description': "Formation en gestion d'entreprise et management.",
                'program': {
                    'name': 'Licence Gestion des Entreprises',
                    'code': 'LIC-GE',
                    'description': 'Formation en management, marketing et gestion de projet.',
                    'tuition_fee': 250000,
                    'duration_years': 3,
                },
                'courses_s1': [
                    ('Management des Organisations', 'GEST101', 5, 25, 15, 0),
                    ('Marketing Fondamental', 'GEST102', 4, 25, 10, 0),
                    ('Comptabilité Analytique', 'GEST103', 5, 30, 15, 0),
                    ('Droit des Affaires', 'GEST104', 4, 25, 10, 0),
                    ('Informatique de Gestion', 'GEST105', 2, 20, 0, 15),
                ],
                'courses_s2': [
                    ('Gestion des Ressources Humaines', 'GEST201', 5, 25, 15, 0),
                    ('Gestion de Projet', 'GEST202', 4, 25, 10, 0),
                    ('Finance d\'Entreprise', 'GEST203', 5, 30, 15, 0),
                    ('Marketing Digital', 'GEST204', 4, 25, 10, 10),
                    ('Communication Professionnelle', 'GEST205', 2, 20, 10, 0),
                ],
            },
        ],
    },
]

CLASSROOMS = [
    ('Amphi A', 'AMP-A', 'Bâtiment Principal', 200, True, False),
    ('Amphi B', 'AMP-B', 'Bâtiment Principal', 150, True, False),
    ('Salle 101', 'S101', 'Bâtiment A', 50, True, False),
    ('Salle 102', 'S102', 'Bâtiment A', 50, True, False),
    ('Salle 201', 'S201', 'Bâtiment B', 40, True, False),
    ('Salle 202', 'S202', 'Bâtiment B', 40, False, False),
    ('Salle Info 1', 'SINFO1', 'Bâtiment C', 30, True, True),
    ('Salle Info 2', 'SINFO2', 'Bâtiment C', 30, True, True),
    ('Labo Physique', 'LAB-PHY', 'Bâtiment D', 25, True, False),
    ('Salle de Conférence', 'CONF', 'Administration', 80, True, False),
]

TIME_SLOTS = [
    (0, '08:00', '09:30'),  # Monday 08h-09h30
    (0, '10:00', '11:30'),
    (0, '14:00', '15:30'),
    (0, '16:00', '17:30'),
    (1, '08:00', '09:30'),  # Tuesday
    (1, '10:00', '11:30'),
    (1, '14:00', '15:30'),
    (1, '16:00', '17:30'),
    (2, '08:00', '09:30'),  # Wednesday
    (2, '10:00', '11:30'),
    (2, '14:00', '15:30'),
    (3, '08:00', '09:30'),  # Thursday
    (3, '10:00', '11:30'),
    (3, '14:00', '15:30'),
    (3, '16:00', '17:30'),
    (4, '08:00', '09:30'),  # Friday
    (4, '10:00', '11:30'),
    (4, '14:00', '15:30'),
    (5, '08:00', '09:30'),  # Saturday
    (5, '10:00', '11:30'),
]

TEACHER_SPECIALIZATIONS = [
    'Informatique', 'Mathématiques', 'Physique', 'Chimie',
    'Littérature', 'Linguistique', 'Pédagogie', 'Économie',
    'Gestion', 'Droit', 'Statistiques', 'Sociologie',
    'Anglais', 'Communication', 'Management',
]


class Command(BaseCommand):
    help = 'Populates the database with realistic Malian university data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🌱 Starting database seeding...'))

        if options['clear']:
            self._clear_data()

        with transaction.atomic():
            self._create_academic_structure()
            self._create_classrooms()
            self._create_admin_user()
            self._create_teachers()
            self._create_students()
            self._create_enrollments()
            self._create_courses_and_assign_teachers()
            self._create_time_slots_and_schedules()
            self._create_exams()
            self._create_grades()
            self._calculate_course_grades()
            self._create_financial_data()
            self._run_deliberation()
            self._create_next_academic_year()

        self.stdout.write(self.style.SUCCESS('✅ Database seeding complete!'))
        self._print_summary()

    def _clear_data(self):
        """Clear test data (preserving superusers)."""
        from apps.students.models import Student, Enrollment, StudentPromotion
        from apps.teachers.models import Teacher, TeacherCourse, TeacherContract
        from apps.academics.models import Course, Exam, Grade, CourseGrade, ReportCard
        from apps.university.models import (
            AcademicYear, Semester, Faculty, Department, Program, Level, Classroom
        )
        from apps.scheduling.models import TimeSlot, Schedule, CourseSession
        from apps.finance.models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense

        self.stdout.write('  Clearing existing data...')
        StudentPromotion.objects.all().delete()
        ReportCard.objects.all().delete()
        CourseGrade.objects.all().delete()
        Grade.objects.all().delete()
        Exam.objects.all().delete()
        CourseSession.objects.all().delete()
        Schedule.objects.all().delete()
        TimeSlot.objects.all().delete()
        TeacherCourse.objects.all().delete()
        TeacherContract.objects.all().delete()
        StudentBalance.objects.all().delete()
        TuitionPayment.objects.all().delete()
        TuitionFee.objects.all().delete()
        Salary.objects.all().delete()
        Expense.objects.all().delete()
        Enrollment.objects.all().delete()
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        Course.objects.all().delete()
        Program.objects.all().delete()
        Department.objects.all().delete()
        Faculty.objects.all().delete()
        Level.objects.all().delete()
        Classroom.objects.all().delete()
        Semester.objects.all().delete()
        AcademicYear.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('  ✓ Data cleared'))

    # =====================================================================
    # 1. Academic Structure
    # =====================================================================
    def _create_academic_structure(self):
        from apps.university.models import AcademicYear, Semester, Faculty, Department, Level, Program

        self.stdout.write('  Creating academic structure...')

        # Academic Year 2025-2026
        self.academic_year, _ = AcademicYear.objects.get_or_create(
            name='2025-2026',
            defaults={
                'start_date': date(2025, 10, 1),
                'end_date': date(2026, 7, 31),
                'is_current': True,
            }
        )

        # Semesters
        self.semester_s1, _ = Semester.objects.get_or_create(
            academic_year=self.academic_year,
            semester_type='S1',
            defaults={
                'start_date': date(2025, 10, 1),
                'end_date': date(2026, 2, 15),
                'is_current': False,
            }
        )
        self.semester_s2, _ = Semester.objects.get_or_create(
            academic_year=self.academic_year,
            semester_type='S2',
            defaults={
                'start_date': date(2026, 2, 16),
                'end_date': date(2026, 7, 31),
                'is_current': True,
            }
        )

        # Levels
        self.levels = {}
        level_data = [
            ('L1', 1), ('L2', 2), ('L3', 3), ('M1', 4), ('M2', 5),
        ]
        for name, order in level_data:
            level, _ = Level.objects.get_or_create(name=name, defaults={'order': order})
            self.levels[name] = level

        # Faculties, Departments, Programs
        self.faculties = []
        self.departments = []
        self.programs = []
        self.dept_data = {}

        for fac_data in FACULTIES:
            faculty, _ = Faculty.objects.get_or_create(
                code=fac_data['code'],
                defaults={
                    'name': fac_data['name'],
                    'description': fac_data['description'],
                }
            )
            self.faculties.append(faculty)

            for dept_data in fac_data['departments']:
                department, _ = Department.objects.get_or_create(
                    code=dept_data['code'],
                    defaults={
                        'name': dept_data['name'],
                        'faculty': faculty,
                        'description': dept_data['description'],
                    }
                )
                self.departments.append(department)

                prog_info = dept_data['program']
                program, _ = Program.objects.get_or_create(
                    code=prog_info['code'],
                    defaults={
                        'name': prog_info['name'],
                        'department': department,
                        'duration_years': prog_info['duration_years'],
                        'description': prog_info['description'],
                        'tuition_fee': Decimal(str(prog_info['tuition_fee'])),
                    }
                )
                # Add L1, L2, L3 levels
                program.levels.set([self.levels['L1'], self.levels['L2'], self.levels['L3']])
                self.programs.append(program)

                # Store course data for later
                self.dept_data[program.id] = {
                    'courses_s1': dept_data['courses_s1'],
                    'courses_s2': dept_data['courses_s2'],
                    'department': department,
                }

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ {len(self.faculties)} faculties, {len(self.departments)} departments, '
            f'{len(self.programs)} programs, {len(self.levels)} levels'
        ))

    # =====================================================================
    # 2. Classrooms
    # =====================================================================
    def _create_classrooms(self):
        from apps.university.models import Classroom

        self.stdout.write('  Creating classrooms...')
        self.classrooms = []
        for name, code, building, capacity, projector, computers in CLASSROOMS:
            classroom, _ = Classroom.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'building': building,
                    'capacity': capacity,
                    'has_projector': projector,
                    'has_computers': computers,
                }
            )
            self.classrooms.append(classroom)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.classrooms)} classrooms'))

    # =====================================================================
    # 3. Admin User
    # =====================================================================
    def _create_admin_user(self):
        self.stdout.write('  Creating admin user...')
        self.admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@attawoune.edu.ml',
                'first_name': 'Administrateur',
                'last_name': 'Système',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'gender': 'M',
            }
        )
        if created:
            self.admin_user.set_password('Admin@2025!')
            self.admin_user.save()
        else:
            # Always reset password in case it was changed
            self.admin_user.set_password('Admin@2025!')
            self.admin_user.save()
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Admin user: admin / Admin@2025!'
        ))

    # =====================================================================
    # 4. Teachers
    # =====================================================================
    def _create_teachers(self):
        from apps.teachers.models import Teacher

        self.stdout.write('  Creating teachers...')
        self.teachers = []
        used_usernames = set()

        for i in range(15):
            gender = random.choice(['M', 'F'])
            first_name = random.choice(
                MALE_FIRST_NAMES if gender == 'M' else FEMALE_FIRST_NAMES
            )
            last_name = random.choice(LAST_NAMES)

            username = f"ens_{first_name.lower().replace('é', 'e').replace('ï', 'i').replace('ô', 'o')}_{last_name.lower().replace('é', 'e').replace('ï', 'i').replace('ô', 'o')}"
            # Ensure unique
            while username in used_usernames:
                username = f"{username}_{random.randint(1, 99)}"
            used_usernames.add(username)

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@attawoune.edu.ml',
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'TEACHER',
                    'gender': gender,
                    'phone': f'+223 {random.randint(60, 79)}{random.randint(100000, 999999)}',
                }
            )
            if created:
                user.set_password('Teacher@2025!')
                user.save()

            dept = self.departments[i % len(self.departments)]
            rank = random.choice(['ASSISTANT', 'LECTURER', 'SENIOR_LECTURER', 'PROFESSOR'])
            contract = random.choice(['PERMANENT', 'CONTRACT', 'VISITING'])
            spec = TEACHER_SPECIALIZATIONS[i % len(TEACHER_SPECIALIZATIONS)]

            teacher, _ = Teacher.objects.get_or_create(
                user=user,
                defaults={
                    'department': dept,
                    'rank': rank,
                    'contract_type': contract,
                    'hire_date': date(
                        random.randint(2015, 2024),
                        random.randint(1, 12),
                        random.randint(1, 28)
                    ),
                    'specialization': spec,
                    'office_location': f'Bureau {chr(65 + i % 6)}{random.randint(1, 10):02d}',
                }
            )
            self.teachers.append(teacher)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.teachers)} teachers'))

    # =====================================================================
    # 5. Students
    # =====================================================================
    def _create_students(self):
        from apps.students.models import Student

        self.stdout.write('  Creating students...')
        self.students = []
        used_usernames = set()

        students_per_program = [20, 18, 15, 15, 17, 15]  # = 100

        for prog_idx, program in enumerate(self.programs):
            count = students_per_program[prog_idx]
            for j in range(count):
                gender = random.choice(['M', 'F'])
                first_name = random.choice(
                    MALE_FIRST_NAMES if gender == 'M' else FEMALE_FIRST_NAMES
                )
                last_name = random.choice(LAST_NAMES)

                username = f"etu_{first_name.lower().replace('é', 'e').replace('ï', 'i').replace('ô', 'o')}_{last_name.lower().replace('é', 'e').replace('ï', 'i').replace('ô', 'o')}"
                while username in used_usernames:
                    username = f"{username}_{random.randint(1, 999)}"
                used_usernames.add(username)

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f'{username}@etud.attawoune.edu.ml',
                        'first_name': first_name,
                        'last_name': last_name,
                        'role': 'STUDENT',
                        'gender': gender,
                        'phone': f'+223 {random.randint(60, 79)}{random.randint(100000, 999999)}',
                        'date_of_birth': date(
                            random.randint(1998, 2006),
                            random.randint(1, 12),
                            random.randint(1, 28)
                        ),
                    }
                )
                if created:
                    user.set_password('Student@2025!')
                    user.save()

                # Assign level: mostly L1, some L2
                level = random.choices(
                    [self.levels['L1'], self.levels['L2']],
                    weights=[70, 30]
                )[0]

                student, _ = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        'program': program,
                        'current_level': level,
                        'enrollment_date': date(2025, 10, random.randint(1, 15)),
                        'status': 'ACTIVE',
                        'guardian_name': f'{random.choice(MALE_FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                        'guardian_phone': f'+223 {random.randint(60, 79)}{random.randint(100000, 999999)}',
                    }
                )
                self.students.append(student)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.students)} students'))

    # =====================================================================
    # 6. Enrollments
    # =====================================================================
    def _create_enrollments(self):
        from apps.students.models import Enrollment

        self.stdout.write('  Creating enrollments...')
        count = 0
        for student in self.students:
            _, created = Enrollment.objects.get_or_create(
                student=student,
                academic_year=self.academic_year,
                defaults={
                    'program': student.program,
                    'level': student.current_level,
                    'status': 'ENROLLED',
                    'is_active': True,
                }
            )
            if created:
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} enrollments'))

    # =====================================================================
    # 7. Courses + Teacher Assignments
    # =====================================================================
    def _create_courses_and_assign_teachers(self):
        from apps.academics.models import Course
        from apps.teachers.models import TeacherCourse

        self.stdout.write('  Creating courses and assigning teachers...')
        self.courses = []
        teacher_idx = 0

        for program in self.programs:
            prog_data = self.dept_data[program.id]

            for sem_type, semester, course_list_key in [
                ('S1', self.semester_s1, 'courses_s1'),
                ('S2', self.semester_s2, 'courses_s2'),
            ]:
                for name, code, credits, hours_lecture, hours_tutorial, hours_practical in prog_data[course_list_key]:
                    course, _ = Course.objects.get_or_create(
                        code=code,
                        defaults={
                            'name': name,
                            'program': program,
                            'level': self.levels['L1'],
                            'semester_type': sem_type,
                            'credits': credits,
                            'hours_lecture': hours_lecture,
                            'hours_tutorial': hours_tutorial,
                            'hours_practical': hours_practical,
                            'course_type': 'REQUIRED',
                        }
                    )
                    self.courses.append(course)

                    # Assign teacher
                    teacher = self.teachers[teacher_idx % len(self.teachers)]
                    teacher_idx += 1

                    TeacherCourse.objects.get_or_create(
                        teacher=teacher,
                        course=course,
                        semester=semester,
                        defaults={'is_primary': True}
                    )

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.courses)} courses with teacher assignments'))

    # =====================================================================
    # 8. Time Slots + Schedules
    # =====================================================================
    def _create_time_slots_and_schedules(self):
        from apps.scheduling.models import TimeSlot, Schedule
        from apps.teachers.models import TeacherCourse

        self.stdout.write('  Creating time slots and schedules...')

        # Create time slots
        self.time_slots = []
        for day, start, end in TIME_SLOTS:
            ts, _ = TimeSlot.objects.get_or_create(
                day=day,
                start_time=time.fromisoformat(start),
                end_time=time.fromisoformat(end),
            )
            self.time_slots.append(ts)

        # Create schedules for S1 courses
        slot_idx = 0
        room_idx = 0
        assignments = TeacherCourse.objects.filter(semester=self.semester_s1)
        for assignment in assignments:
            slot = self.time_slots[slot_idx % len(self.time_slots)]
            room = self.classrooms[room_idx % len(self.classrooms)]

            Schedule.objects.get_or_create(
                course=assignment.course,
                teacher=assignment.teacher,
                semester=self.semester_s1,
                defaults={
                    'time_slot': slot,
                    'classroom': room,
                }
            )
            slot_idx += 1
            room_idx += 1

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ {len(self.time_slots)} time slots, {assignments.count()} schedules'
        ))

    # =====================================================================
    # 9. Exams
    # =====================================================================
    def _create_exams(self):
        from apps.academics.models import Exam

        self.stdout.write('  Creating exams...')
        self.exams = []

        for course in self.courses:
            # Midterm
            midterm, _ = Exam.objects.get_or_create(
                course=course,
                exam_type='MIDTERM',
                semester=self.semester_s1 if course.semester_type == 'S1' else self.semester_s2,
                defaults={
                    'date': date(2026, 1, random.randint(5, 20)) if course.semester_type == 'S1'
                            else date(2026, 5, random.randint(5, 20)),
                    'start_time': time(8, 0),
                    'end_time': time(10, 0),
                    'max_score': Decimal('20.00'),
                    'weight': Decimal('0.40'),
                }
            )
            self.exams.append(midterm)

            # Final
            final, _ = Exam.objects.get_or_create(
                course=course,
                exam_type='FINAL',
                semester=self.semester_s1 if course.semester_type == 'S1' else self.semester_s2,
                defaults={
                    'date': date(2026, 2, random.randint(1, 10)) if course.semester_type == 'S1'
                            else date(2026, 7, random.randint(1, 15)),
                    'start_time': time(8, 0),
                    'end_time': time(11, 0),
                    'max_score': Decimal('20.00'),
                    'weight': Decimal('0.60'),
                }
            )
            self.exams.append(final)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.exams)} exams'))

    # =====================================================================
    # 10. Grades
    # =====================================================================
    def _create_grades(self):
        from apps.academics.models import Grade, Exam

        self.stdout.write('  Creating grades (this may take a moment)...')
        grade_count = 0

        for student in self.students:
            # Get courses for this student's program
            program_courses = [c for c in self.courses if c.program == student.program]

            for course in program_courses:
                exams = Exam.objects.filter(course=course)
                for exam in exams:
                    # Generate realistic grade with bell curve
                    # Mean ~12, std ~3, clamped to [0, 20]
                    score = round(random.gauss(12, 3), 2)
                    score = max(0, min(20, score))

                    # Some students are absent occasionally (3%)
                    is_absent = random.random() < 0.03

                    Grade.objects.get_or_create(
                        student=student,
                        exam=exam,
                        defaults={
                            'score': Decimal('0.00') if is_absent else Decimal(str(score)),
                            'is_absent': is_absent,
                            'graded_by': self.admin_user,
                            'remarks': 'Absent(e)' if is_absent else '',
                        }
                    )
                    grade_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {grade_count} grades'))

    # =====================================================================
    # 11. Calculate Course Grades
    # =====================================================================
    def _calculate_course_grades(self):
        from apps.academics.models import Course, Exam, Grade, CourseGrade

        self.stdout.write('  Calculating course grades...')
        count = 0

        for student in self.students:
            program_courses = [c for c in self.courses if c.program == student.program]

            for course in program_courses:
                semester = self.semester_s1 if course.semester_type == 'S1' else self.semester_s2
                exams = Exam.objects.filter(course=course, semester=semester)

                if not exams.exists():
                    continue

                total_weighted = Decimal('0.00')
                total_weight = Decimal('0.00')

                for exam in exams:
                    grade = Grade.objects.filter(student=student, exam=exam).first()
                    if grade and not grade.is_absent:
                        normalized = (grade.score / exam.max_score) * Decimal('20.00')
                        total_weighted += normalized * exam.weight
                        total_weight += exam.weight
                    elif grade and grade.is_absent:
                        total_weight += exam.weight  # 0 score counts

                final_grade = (total_weighted / total_weight) if total_weight > 0 else Decimal('0.00')

                CourseGrade.objects.update_or_create(
                    student=student,
                    course=course,
                    semester=semester,
                    defaults={
                        'final_score': round(final_grade, 2),
                        'is_validated': True,
                        'validated_by': self.admin_user,
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count} course grades calculated'))

    # =====================================================================
    # 12. Run Deliberation
    # =====================================================================
    def _run_deliberation(self):
        from apps.academics.services.deliberation import DeliberationService

        self.stdout.write('  Running deliberation...')
        results = {'PROMOTED': 0, 'REPEATED': 0, 'errors': 0}

        for student in self.students:
            try:
                promotion = DeliberationService.deliberate_student(
                    student, self.academic_year
                )
                decision = promotion.decision
                if decision == 'PROMOTED':
                    results['PROMOTED'] += 1
                else:
                    results['REPEATED'] += 1
            except Exception as e:
                results['errors'] += 1
                self.stdout.write(self.style.WARNING(
                    f'    ⚠ Error for {student}: {e}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f"  ✓ Deliberation: {results['PROMOTED']} promoted, "
            f"{results['REPEATED']} repeated, {results['errors']} errors"
        ))

    # =====================================================================
    # 13. Create Next Academic Year
    # =====================================================================
    def _create_next_academic_year(self):
        from apps.university.models import AcademicYear, Semester
        from apps.students.models import Enrollment, StudentPromotion

        self.stdout.write('  Creating next academic year (2026-2027)...')

        next_year, _ = AcademicYear.objects.get_or_create(
            name='2026-2027',
            defaults={
                'start_date': date(2026, 10, 1),
                'end_date': date(2027, 7, 31),
                'is_current': False,
            }
        )

        Semester.objects.get_or_create(
            academic_year=next_year,
            semester_type='S1',
            defaults={
                'start_date': date(2026, 10, 1),
                'end_date': date(2027, 2, 15),
            }
        )
        Semester.objects.get_or_create(
            academic_year=next_year,
            semester_type='S2',
            defaults={
                'start_date': date(2027, 2, 16),
                'end_date': date(2027, 7, 31),
            }
        )

        # Enroll promoted students in next year at next level
        promotions = StudentPromotion.objects.filter(
            academic_year=self.academic_year
        )
        enrolled_count = 0
        for promo in promotions:
            student = promo.student
            if promo.decision == 'PROMOTED':
                new_level = promo.level_to
                status = 'ENROLLED'
            else:
                new_level = promo.level_from
                status = 'REPEATED'

            # Update student current level
            student.current_level = new_level
            student.save()

            _, created = Enrollment.objects.get_or_create(
                student=student,
                academic_year=next_year,
                defaults={
                    'program': student.program,
                    'level': new_level,
                    'status': status,
                    'is_active': True,
                }
            )
            if created:
                enrolled_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Academic year 2026-2027 created with {enrolled_count} enrollments'
        ))

    # =====================================================================
    # 14. Financial Data
    # =====================================================================
    def _create_financial_data(self):
        from apps.finance.models import TuitionFee, TuitionPayment, StudentBalance, Salary, Expense

        self.stdout.write('  Creating financial data...')

        # --- Tuition Fees per Program ---
        tuition_fees = []
        for program in self.programs:
            fee, _ = TuitionFee.objects.get_or_create(
                program=program,
                academic_year=self.academic_year,
                defaults={
                    'amount': program.tuition_fee,
                    'installments_allowed': 3,
                    'due_date': date(2025, 12, 31),
                }
            )
            tuition_fees.append(fee)
        self.stdout.write(self.style.SUCCESS(f'    ✓ {len(tuition_fees)} tuition fee configs'))

        # --- Tuition Payments & Student Balances ---
        payment_count = 0
        balance_count = 0
        payment_methods = ['CASH', 'BANK_TRANSFER', 'MOBILE_MONEY', 'CHECK']

        for student in self.students:
            fee_amount = student.program.tuition_fee

            # Create student balance
            balance, _ = StudentBalance.objects.get_or_create(
                student=student,
                academic_year=self.academic_year,
                defaults={
                    'total_due': fee_amount,
                    'total_paid': Decimal('0.00'),
                }
            )
            balance_count += 1

            # Simulate payment patterns:
            # 50% fully paid, 30% partial (1-2 installments), 20% pending
            roll = random.random()
            if roll < 0.50:
                # Fully paid in 1-3 installments
                num_installments = random.choice([1, 2, 3])
                installment_amount = fee_amount / num_installments
                total_paid = Decimal('0.00')
                for inst in range(num_installments):
                    pay_date = date(2025, 10 + inst, random.randint(1, 28))
                    ref = f"PAY-{self.academic_year.name[:4]}-{student.student_id}-{inst+1}"
                    TuitionPayment.objects.get_or_create(
                        reference=ref,
                        defaults={
                            'student': student,
                            'academic_year': self.academic_year,
                            'amount': installment_amount,
                            'payment_method': random.choice(payment_methods),
                            'status': 'COMPLETED',
                            'description': f'Tranche {inst+1}/{num_installments}',
                            'receipt_number': f'REC-{random.randint(10000, 99999)}',
                            'payment_date': pay_date,
                            'received_by': self.admin_user,
                        }
                    )
                    total_paid += installment_amount
                    payment_count += 1
                balance.total_paid = total_paid
                balance.save()

            elif roll < 0.80:
                # Partial payment (1 installment out of 3)
                installment_amount = (fee_amount / 3).quantize(Decimal('0.01'))
                ref = f"PAY-{self.academic_year.name[:4]}-{student.student_id}-1"
                TuitionPayment.objects.get_or_create(
                    reference=ref,
                    defaults={
                        'student': student,
                        'academic_year': self.academic_year,
                        'amount': installment_amount,
                        'payment_method': random.choice(payment_methods),
                        'status': 'COMPLETED',
                        'description': 'Tranche 1/3',
                        'receipt_number': f'REC-{random.randint(10000, 99999)}',
                        'payment_date': date(2025, 10, random.randint(1, 28)),
                        'received_by': self.admin_user,
                    }
                )
                payment_count += 1
                balance.total_paid = installment_amount
                balance.save()
            # else: 20% have not paid at all (balance stays at 0 paid)

        self.stdout.write(self.style.SUCCESS(
            f'    ✓ {payment_count} tuition payments, {balance_count} student balances'
        ))

        # --- Teacher Salaries (Oct 2025 - Feb 2026) ---
        salary_count = 0
        salary_base = {
            'PROFESSOR': Decimal('800000'),
            'SENIOR_LECTURER': Decimal('600000'),
            'LECTURER': Decimal('450000'),
            'ASSISTANT': Decimal('350000'),
        }
        for teacher in self.teachers:
            base = salary_base.get(teacher.rank, Decimal('400000'))
            for month in [10, 11, 12, 1, 2]:  # Oct-Dec 2025, Jan-Feb 2026
                year = 2025 if month >= 10 else 2026
                bonuses = Decimal(str(random.choice([0, 25000, 50000, 75000])))
                deductions = Decimal(str(random.choice([15000, 25000, 35000])))
                is_paid = (month <= 12 and year == 2025) or (month == 1 and year == 2026)

                Salary.objects.get_or_create(
                    employee=teacher.user,
                    month=month,
                    year=year,
                    defaults={
                        'base_salary': base,
                        'bonuses': bonuses,
                        'deductions': deductions,
                        'net_salary': base + bonuses - deductions,
                        'status': 'PAID' if is_paid else 'PENDING',
                        'payment_date': date(year, month, 27) if is_paid else None,
                        'processed_by': self.admin_user,
                    }
                )
                salary_count += 1

        self.stdout.write(self.style.SUCCESS(f'    ✓ {salary_count} salary records'))

        # --- University Expenses ---
        expense_data = [
            ('UTILITIES', 'Facture électricité - Octobre', 450000, date(2025, 10, 15)),
            ('UTILITIES', 'Facture eau - Octobre', 120000, date(2025, 10, 20)),
            ('MAINTENANCE', 'Réparation climatisation Amphi A', 350000, date(2025, 10, 25)),
            ('EQUIPMENT', 'Achat 10 ordinateurs Salle Info 1', 5500000, date(2025, 11, 5)),
            ('SUPPLIES', 'Fournitures bureau administration', 175000, date(2025, 11, 10)),
            ('UTILITIES', 'Facture électricité - Novembre', 480000, date(2025, 11, 15)),
            ('UTILITIES', 'Facture eau - Novembre', 115000, date(2025, 11, 20)),
            ('MAINTENANCE', 'Entretien jardin et espaces verts', 200000, date(2025, 12, 1)),
            ('EQUIPMENT', 'Vidéoprojecteur Salle 201', 750000, date(2025, 12, 10)),
            ('UTILITIES', 'Facture électricité - Décembre', 520000, date(2025, 12, 15)),
            ('SUPPLIES', 'Papier et toner imprimantes', 95000, date(2026, 1, 5)),
            ('UTILITIES', 'Facture électricité - Janvier', 460000, date(2026, 1, 15)),
            ('MAINTENANCE', 'Peinture salles Bâtiment B', 680000, date(2026, 1, 20)),
            ('OTHER', 'Organisation cérémonie rentrée académique', 850000, date(2025, 10, 1)),
            ('EQUIPMENT', 'Mobilier salle de conférence', 1200000, date(2026, 2, 1)),
        ]
        expense_count = 0
        for category, description, amount, exp_date in expense_data:
            Expense.objects.get_or_create(
                description=description,
                date=exp_date,
                defaults={
                    'category': category,
                    'amount': Decimal(str(amount)),
                    'approved_by': self.admin_user,
                    'created_by': self.admin_user,
                }
            )
            expense_count += 1

        self.stdout.write(self.style.SUCCESS(f'    ✓ {expense_count} expense records'))
        self.stdout.write(self.style.SUCCESS('  ✓ Financial data complete'))

    # =====================================================================
    # Summary
    # =====================================================================
    def _print_summary(self):
        from apps.students.models import Student, Enrollment
        from apps.teachers.models import Teacher
        from apps.academics.models import Course, Exam, Grade, CourseGrade
        from apps.university.models import AcademicYear, Faculty, Program
        from apps.finance.models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  DATABASE SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Academic Years:    {AcademicYear.objects.count()}')
        self.stdout.write(f'  Faculties:         {Faculty.objects.count()}')
        self.stdout.write(f'  Programs:          {Program.objects.count()}')
        self.stdout.write(f'  Teachers:          {Teacher.objects.count()}')
        self.stdout.write(f'  Students:          {Student.objects.count()}')
        self.stdout.write(f'  Enrollments:       {Enrollment.objects.count()}')
        self.stdout.write(f'  Courses:           {Course.objects.count()}')
        self.stdout.write(f'  Exams:             {Exam.objects.count()}')
        self.stdout.write(f'  Grades:            {Grade.objects.count()}')
        self.stdout.write(f'  Course Grades:     {CourseGrade.objects.count()}')
        self.stdout.write(f'  Tuition Fees:      {TuitionFee.objects.count()}')
        self.stdout.write(f'  Payments:          {TuitionPayment.objects.count()}')
        self.stdout.write(f'  Student Balances:  {StudentBalance.objects.count()}')
        self.stdout.write(f'  Salaries:          {Salary.objects.count()}')
        self.stdout.write(f'  Expenses:          {Expense.objects.count()}')
        self.stdout.write(f'  Users (total):     {User.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('  LOGIN CREDENTIALS:'))
        self.stdout.write(f'  Admin:    admin / Admin@2025!')
        self.stdout.write(f'  Teachers: ens_* / Teacher@2025!')
        self.stdout.write(f'  Students: etu_* / Student@2025!')
        self.stdout.write(self.style.SUCCESS('=' * 60))
