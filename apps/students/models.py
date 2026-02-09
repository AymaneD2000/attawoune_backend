from django.db import models
from django.conf import settings


class Student(models.Model):
    """Profil étudiant lié à un utilisateur."""

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        GRADUATED = 'GRADUATED', 'Diplômé'
        SUSPENDED = 'SUSPENDED', 'Suspendu'
        DROPPED = 'DROPPED', 'Abandonné'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        limit_choices_to={'role': 'STUDENT'},
        verbose_name="Utilisateur"
    )
    student_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Matricule"
    )
    program = models.ForeignKey(
        'university.Program',
        on_delete=models.PROTECT,
        related_name='students',
        verbose_name="Programme"
    )
    current_level = models.ForeignKey(
        'university.Level',
        on_delete=models.PROTECT,
        related_name='current_students',
        verbose_name="Niveau actuel"
    )
    enrollment_date = models.DateField(verbose_name="Date d'inscription")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Statut"
    )
    guardian_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom du tuteur"
    )
    guardian_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone du tuteur"
    )
    emergency_contact = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Contact d'urgence"
    )
    photo = models.ImageField(
        upload_to='students/photos/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"
        ordering = ['student_id']

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.generate_student_id()
        super().save(*args, **kwargs)

    def generate_student_id(self):
        """
        Génère un matricule au format: [FACULTY][YY][YY+1][GENDER][INITIAL][SEQ]
        Exemple: FST1920MA007817
        """
        # 1. Faculty Code
        faculty_code = self.program.department.faculty.code.upper()
        
        # 2. Academic Year (YY + YY+1)
        # Assuming enrollment_date is set, otherwise use current date
        from django.utils import timezone
        date = self.enrollment_date or timezone.now().date()
        year = date.year
        # If enrollment is roughly in Sept-Dec, it's the start of year (e.g. 2019 -> 1920)
        # If Jan-Aug, it belongs to previous start year (e.g. 2020 -> 1920)
        # However, simplistic approach based on input year:
        # User said "19 20 is the year of inscription like 2019 - 2020"
        # Let's take the year of enrollment date as the start year.
        yy = year % 100
        yy_next = (yy + 1) % 100
        year_str = f"{yy:02d}{yy_next:02d}"
        
        # 3. Gender (M/F)
        # Ensure user gender is available
        gender = self.user.gender if hasattr(self.user, 'gender') else 'M'
        
        # 4. Initial (First letter of First Name - User said "A is the first letter of name here Aymane")
        # Usually name = First Name.
        initial = self.user.first_name[0].upper() if self.user.first_name else 'X'
        
        prefix = f"{faculty_code}{year_str}{gender}{initial}"
        
        # 5. Sequence (6 digits)
        # Find last student with this prefix
        last_student = Student.objects.filter(student_id__startswith=prefix).order_by('-student_id').first()
        
        if last_student:
            # Extract last 6 digits
            try:
                last_seq = int(last_student.student_id[-6:])
                new_seq = last_seq + 1
            except ValueError:
                new_seq = 1
        else:
            new_seq = 1
            
        self.student_id = f"{prefix}{new_seq:06d}"

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name()}"


class Enrollment(models.Model):
    """Inscription d'un étudiant pour une année académique."""

    class EnrollmentStatus(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Inscrit'
        PROMOTED = 'PROMOTED', 'Promu'
        REPEATED = 'REPEATED', 'Redoublant'
        TRANSFERRED = 'TRANSFERRED', 'Transféré'

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name="Étudiant"
    )
    academic_year = models.ForeignKey(
        'university.AcademicYear',
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name="Année académique"
    )
    program = models.ForeignKey(
        'university.Program',
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name="Programme"
    )
    level = models.ForeignKey(
        'university.Level',
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name="Niveau"
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
        verbose_name="Statut"
    )
    enrollment_date = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        unique_together = ['student', 'academic_year']
        ordering = ['-academic_year', 'student']

    def __str__(self):
        return f"{self.student} - {self.academic_year} ({self.level})"


class Attendance(models.Model):
    """Présence des étudiants aux cours."""

    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', 'Présent'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'En retard'
        EXCUSED = 'EXCUSED', 'Excusé'

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Étudiant"
    )
    course_session = models.ForeignKey(
        'scheduling.CourseSession',
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Séance de cours"
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        verbose_name="Statut"
    )
    remarks = models.TextField(blank=True, verbose_name="Remarques")
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_attendances',
        verbose_name="Enregistré par"
    )

    class Meta:
        verbose_name = "Présence"
        verbose_name_plural = "Présences"
        unique_together = ['student', 'course_session']

    def __str__(self):
        return f"{self.student} - {self.course_session} ({self.get_status_display()})"


class StudentPromotion(models.Model):
    """Historique des promotions/délibérations annuelles."""

    class PromotionDecision(models.TextChoices):
        PROMOTED = 'PROMOTED', 'Admis(e)'
        REPEATED = 'REPEATED', 'Redoublant(e)'
        FAILED = 'FAILED', 'Exclu(e)/Echec'
        CONDITIONAL = 'CONDITIONAL', 'Admis(e) avec dettes'

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='promotions',
        verbose_name="Étudiant"
    )
    academic_year = models.ForeignKey(
        'university.AcademicYear',
        on_delete=models.CASCADE,
        related_name='promotions',
        verbose_name="Année académique"
    )
    program = models.ForeignKey(
        'university.Program',
        on_delete=models.PROTECT,
        verbose_name="Programme"
    )
    level_from = models.ForeignKey(
        'university.Level',
        on_delete=models.PROTECT,
        related_name='promotions_from',
        verbose_name="Niveau précédent"
    )
    level_to = models.ForeignKey(
        'university.Level',
        on_delete=models.PROTECT,
        related_name='promotions_to',
        verbose_name="Niveau suivant",
        null=True, blank=True
    )
    annual_gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name="Moyenne annuelle"
    )
    decision = models.CharField(
        max_length=20,
        choices=PromotionDecision.choices,
        verbose_name="Décision"
    )
    decision_date = models.DateField(auto_now_add=True, verbose_name="Date de décision")
    remarks = models.TextField(blank=True, verbose_name="Remarques")

    class Meta:
        verbose_name = "Délibération"
        verbose_name_plural = "Délibérations"
        unique_together = ['student', 'academic_year']
        ordering = ['-academic_year', 'student']

    def __str__(self):
        return f"{self.student} - {self.academic_year}: {self.get_decision_display()}"
