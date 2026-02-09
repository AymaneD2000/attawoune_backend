from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Course(models.Model):
    """Cours/Matière."""

    class CourseType(models.TextChoices):
        REQUIRED = 'REQUIRED', 'Obligatoire'
        ELECTIVE = 'ELECTIVE', 'Optionnel'
        PRACTICAL = 'PRACTICAL', 'Travaux pratiques'

    name = models.CharField(max_length=200, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    program = models.ForeignKey(
        'university.Program',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name="Programme"
    )
    course_type = models.CharField(
        max_length=20,
        choices=CourseType.choices,
        default=CourseType.REQUIRED,
        verbose_name="Type de cours"
    )
    credits = models.PositiveIntegerField(default=3, verbose_name="Crédits")
    hours_lecture = models.PositiveIntegerField(default=30, verbose_name="Heures de cours")
    hours_practical = models.PositiveIntegerField(default=0, verbose_name="Heures TP")
    hours_tutorial = models.PositiveIntegerField(default=0, verbose_name="Heures TD")
    description = models.TextField(blank=True, verbose_name="Description")
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='required_for',
        verbose_name="Prérequis"
    )
    semester_type = models.CharField(
        max_length=2,
        choices=[('S1', 'Semestre 1'), ('S2', 'Semestre 2')],
        default='S1',
        verbose_name="Semestre"
    )
    level = models.ForeignKey(
        'university.Level',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name="Niveau",
        null=True  # Temporarily allow null for migration
    )
    coefficient = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal('1.0'),
        verbose_name="Coefficient"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        ordering = ['program', 'level', 'semester_type', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def total_hours(self):
        return self.hours_lecture + self.hours_practical + self.hours_tutorial


class Exam(models.Model):
    """Examen pour un cours."""

    class ExamType(models.TextChoices):
        MIDTERM = 'MIDTERM', 'Partiel'
        FINAL = 'FINAL', 'Final'
        QUIZ = 'QUIZ', 'Quiz'
        PRACTICAL = 'PRACTICAL', 'TP noté'
        PROJECT = 'PROJECT', 'Projet'
        ORAL = 'ORAL', 'Oral'
        RESIT = 'RESIT', 'Rattrapage'

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name="Cours"
    )
    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices,
        verbose_name="Type d'examen"
    )
    semester = models.ForeignKey(
        'university.Semester',
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name="Semestre"
    )
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    classroom = models.ForeignKey(
        'university.Classroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams',
        verbose_name="Salle"
    )
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        verbose_name="Note maximale"
    )
    weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name="Poids"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Examens"
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.course} - {self.get_exam_type_display()} ({self.date})"


class Grade(models.Model):
    """Note d'un étudiant pour un examen."""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name="Étudiant"
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name="Examen"
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Note"
    )
    remarks = models.TextField(blank=True, verbose_name="Remarques")
    is_absent = models.BooleanField(default=False, verbose_name="Absent")
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='graded_exams',
        verbose_name="Noté par"
    )
    graded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        unique_together = ['student', 'exam']
        ordering = ['exam', 'student']

    def __str__(self):
        return f"{self.student} - {self.exam}: {self.score}"

    @property
    def percentage(self):
        if self.exam.max_score > 0:
            return (self.score / self.exam.max_score) * 100
        return 0


class CourseGrade(models.Model):
    """Note finale d'un étudiant pour un cours dans un semestre."""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='course_grades',
        verbose_name="Étudiant"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='student_grades',
        verbose_name="Cours"
    )
    semester = models.ForeignKey(
        'university.Semester',
        on_delete=models.CASCADE,
        related_name='course_grades',
        verbose_name="Semestre"
    )
    final_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name="Note finale"
    )
    grade_letter = models.CharField(
        max_length=2,
        blank=True,
        verbose_name="Mention"
    )
    is_validated = models.BooleanField(default=False, verbose_name="Validé")
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_grades',
        verbose_name="Validé par"
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Note de cours"
        verbose_name_plural = "Notes de cours"
        unique_together = ['student', 'course', 'semester']

    def __str__(self):
        return f"{self.student} - {self.course}: {self.final_score}"

    def save(self, *args, **kwargs):
        # Calculate letter grade
        if self.final_score >= 16:
            self.grade_letter = 'A'
        elif self.final_score >= 14:
            self.grade_letter = 'B'
        elif self.final_score >= 12:
            self.grade_letter = 'C'
        elif self.final_score >= 10:
            self.grade_letter = 'D'
        else:
            self.grade_letter = 'F'
        super().save(*args, **kwargs)


class ReportCard(models.Model):
    """Bulletin de notes pour un étudiant et un semestre."""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='report_cards',
        verbose_name="Étudiant"
    )
    semester = models.ForeignKey(
        'university.Semester',
        on_delete=models.CASCADE,
        related_name='report_cards',
        verbose_name="Semestre"
    )
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Moyenne générale"
    )
    total_credits = models.PositiveIntegerField(default=0, verbose_name="Crédits totaux")
    credits_earned = models.PositiveIntegerField(default=0, verbose_name="Crédits obtenus")
    rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="Rang")
    remarks = models.TextField(blank=True, verbose_name="Observations")
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    published_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_report_cards',
        verbose_name="Généré par"
    )

    class Meta:
        verbose_name = "Bulletin de notes"
        verbose_name_plural = "Bulletins de notes"
        unique_together = ['student', 'semester']
        ordering = ['-semester', 'student']

    def __str__(self):
        return f"Bulletin - {self.student} ({self.semester})"

    def calculate_gpa(self):
        """Calculer la moyenne pondérée."""
        course_grades = CourseGrade.objects.filter(
            student=self.student,
            semester=self.semester
        ).select_related('course')

        total_weighted_score = Decimal('0.00')
        total_credits = 0

        for cg in course_grades:
            credits = cg.course.credits
            total_weighted_score += cg.final_score * credits
            total_credits += credits

        if total_credits > 0:
            self.gpa = total_weighted_score / total_credits
            self.total_credits = total_credits
            self.credits_earned = sum(
                cg.course.credits for cg in course_grades if cg.final_score >= 10
            )
        self.save()
