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

    def _student_id_prefix(self, year):
        """Matricule prefix [FACULTY][YY][YY+1][GENDER][INITIAL] for a start year."""
        # 1. Faculty Code
        faculty_code = self.program.department.faculty.code.upper()

        # 2. Academic Year segment (YY + YY+1)
        yy = year % 100
        yy_next = (yy + 1) % 100
        year_str = f"{yy:02d}{yy_next:02d}"

        # 3. Gender (M/F)
        gender = self.user.gender if hasattr(self.user, 'gender') else 'M'

        # 4. Initial (First letter of First Name)
        initial = self.user.first_name[0].upper() if self.user.first_name else 'X'

        return f"{faculty_code}{year_str}{gender}{initial}"

    @staticmethod
    def _next_student_id_sequence(last_student):
        """Next six-digit sequence after ``last_student`` (or 1 when none)."""
        if last_student:
            try:
                return int(last_student.student_id[-6:]) + 1
            except ValueError:
                return 1
        return 1

    def generate_student_id(self):
        """
        Génère un matricule au format: [FACULTY][YY][YY+1][GENDER][INITIAL][SEQ]
        Exemple: FST1920MA007817
        """
        from django.utils import timezone
        date = self.enrollment_date or timezone.now().date()
        year = date.year

        prefix = self._student_id_prefix(year)
        last_student = Student.objects.filter(student_id__startswith=prefix).order_by('-student_id').first()
        self.student_id = f"{prefix}{self._next_student_id_sequence(last_student):06d}"

    def regenerate_student_id_for_year(self, academic_year):
        """
        Regenerate the matricule using the year segment of ``academic_year``
        (2026 start => ``2627``), keeping faculty/gender/initial and
        allocating the next available sequence for the new prefix.

        Returns the ``(old_student_id, new_student_id)`` pair. The caller is
        responsible for running this inside a transaction (the correction
        service does).
        """
        old_student_id = self.student_id
        prefix = self._student_id_prefix(academic_year.start_date.year)
        last_student = (
            Student.objects.select_for_update()
            .filter(student_id__startswith=prefix)
            .exclude(pk=self.pk)
            .order_by('-student_id')
            .first()
        )
        next_sequence = self._next_student_id_sequence(last_student)
        self.student_id = f"{prefix}{next_sequence:06d}"
        self.save(update_fields=['student_id', 'updated_at'])
        return old_student_id, self.student_id

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
