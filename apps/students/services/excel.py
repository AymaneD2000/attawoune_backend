import io
from datetime import datetime, date
from openpyxl import Workbook, load_workbook
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.core.exceptions import ValidationError
from ..models import Student, Enrollment
from apps.university.models import Program, Level, AcademicYear

User = get_user_model()

class StudentExcelService:
    """Service to handle Excel import/export for students."""

    HEADERS = [
        'Matricule', 'Prénom', 'Nom', 'Email', 'Sexe', 'Date Naissance',
        'Téléphone', 'Code Programme', 'Niveau Actuel', 'Date Inscription',
        'Statut', 'Nom Tuteur', 'Téléphone Tuteur', 'Contact Urgence'
    ]

    @staticmethod
    def export_students(queryset):
        """Export students to an Excel workbook."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Étudiants"

        # Add headers
        ws.append(StudentExcelService.HEADERS)

        # Add student data
        for student in queryset:
            ws.append([
                student.student_id,
                student.user.first_name,
                student.user.last_name,
                student.user.email,
                student.user.get_gender_display(),
                student.user.date_of_birth,
                student.user.phone,
                student.program.code if student.program else "",
                student.current_level.name if student.current_level else "",
                student.enrollment_date,
                student.get_status_display(),
                student.guardian_name,
                student.guardian_phone,
                student.emergency_contact
            ])

        # Write to memory
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def download_template():
        """Generate a template Excel file for student import."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Template Import"

        # Add headers
        ws.append(StudentExcelService.HEADERS)

        # Add an example row
        ws.append([
            "", "Jean", "Dupont", "jean.dupont@example.com", "M", "2000-01-01",
            "+221770000000", "INFO",
            "L1", "2023-10-01", "ACTIVE", "Tuteur Dupont",
            "+221780000000", "Contact Urgence"
        ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def import_students(file_obj):
        """
        Import students from an Excel file.
        Returns (success_count, error_list)
        """
        try:
            wb = load_workbook(file_obj, data_only=True)
        except Exception as e:
            return 0, [f"Format de fichier invalide: {str(e)}"]

        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        
        success_count = 0
        errors = []

        for row_idx, row in enumerate(rows, start=2):
            if not any(row):  # Skip empty rows
                continue

            try:
                with transaction.atomic():
                    # Parse data from row
                    # Headers: Matricule[0], Prénom[1], Nom[2], Email[3], Sexe[4], Date Naissance[5],
                    # Téléphone[6], Code Programme[7], Niveau Actuel[8], Date Inscription[9],
                    # Statut[10], Nom Tuteur[11], Téléphone Tuteur[12], Contact Urgence[13]
                    
                    def parse_date(val):
                        if not val:
                            return None
                        if isinstance(val, (date, datetime)):
                            return val.date() if isinstance(val, datetime) else val
                        if isinstance(val, str):
                            # Try common formats
                            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                                try:
                                    return datetime.strptime(val, fmt).date()
                                except ValueError:
                                    continue
                        return None

                    student_id_val = row[0]
                    first_name = row[1]
                    last_name = row[2]
                    email = row[3]
                    gender = row[4] or 'M'
                    birth_date = parse_date(row[5])
                    phone = row[6]
                    program_code = row[7]
                    level_name = row[8]
                    enroll_date = parse_date(row[9]) or timezone.now().date()
                    status = row[10] or 'ACTIVE'
                    guardian_name = row[11]
                    guardian_phone = row[12]
                    emergency_contact = row[13]

                    if not (first_name and last_name and email and program_code):
                        raise ValidationError("Les champs Prénom, Nom, Email et Code Programme sont obligatoires.")

                    # 1. Handle User
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'role': 'STUDENT',
                            'gender': gender,
                            'date_of_birth': birth_date,
                            'phone': phone,
                        }
                    )
                    
                    if not created:
                        # Ensure user is a student
                        if user.role != 'STUDENT':
                            raise ValidationError(f"L'utilisateur {email} existe déjà et n'est pas un étudiant.")

                    # 2. Find Program and Level
                    program_code_extracted = None
                    if program_code and " - " in str(program_code):
                        program_code_extracted = str(program_code).split(" - ")[0].strip()
                    else:
                        program_code_extracted = str(program_code).strip() if program_code else None

                    program = None
                    if program_code_extracted:
                        program = Program.objects.filter(code__iexact=program_code_extracted).first()
                    
                    if not program:
                        program = Program.objects.filter(name__iexact=program_code).first()
                        
                    if not program:
                        raise ValidationError(f"Programme avec le code '{program_code}' introuvable.")
                    
                    level = None
                    if level_name:
                        level = Level.objects.filter(models.Q(name__iexact=level_name) | models.Q(name__icontains=level_name)).first()
                    
                    if not level and program:
                        # Pick first level for program if not specified? 
                        # Better to error and ask for clarity if level is ambiguous.
                        level = program.levels.first()

                    # 3. Handle Student Profile
                    student, s_created = Student.objects.update_or_create(
                        user=user,
                        defaults={
                            'program': program,
                            'current_level': level,
                            'enrollment_date': enroll_date,
                            'status': status,
                            'guardian_name': guardian_name or "",
                            'guardian_phone': guardian_phone or "",
                            'emergency_contact': emergency_contact or "",
                        }
                    )
                    
                    if student_id_val:
                         student.student_id = student_id_val
                         student.save()

                    # 4. Handle Enrollment for current year
                    try:
                        current_year = AcademicYear.objects.get(is_current=True)
                        Enrollment.objects.get_or_create(
                            student=student,
                            academic_year=current_year,
                            defaults={
                                'program': program,
                                'level': level,
                                'status': 'ENROLLED'
                            }
                        )
                    except AcademicYear.DoesNotExist:
                        pass

                    success_count += 1

            except Exception as e:
                errors.append(f"Ligne {row_idx}: {str(e)}")

        return success_count, errors
