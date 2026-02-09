from django.db import models
from django.conf import settings


class AcademicYear(models.Model):
    """Année académique."""
    name = models.CharField(max_length=50, verbose_name="Nom", unique=True)
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    is_current = models.BooleanField(default=False, verbose_name="Année en cours")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Année académique"
        verbose_name_plural = "Années académiques"
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Semester(models.Model):
    """Semestre d'une année académique."""

    class SemesterType(models.TextChoices):
        FIRST = 'S1', 'Semestre 1'
        SECOND = 'S2', 'Semestre 2'

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='semesters',
        verbose_name="Année académique"
    )
    semester_type = models.CharField(
        max_length=2,
        choices=SemesterType.choices,
        verbose_name="Type de semestre"
    )
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    is_current = models.BooleanField(default=False, verbose_name="Semestre en cours")

    class Meta:
        verbose_name = "Semestre"
        verbose_name_plural = "Semestres"
        unique_together = ['academic_year', 'semester_type']
        ordering = ['academic_year', 'semester_type']

    def __str__(self):
        return f"{self.get_semester_type_display()} - {self.academic_year}"


class Faculty(models.Model):
    """Faculté de l'université."""
    name = models.CharField(max_length=200, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    description = models.TextField(blank=True, verbose_name="Description")
    dean = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faculty_dean',
        limit_choices_to={'role': 'DEAN'},
        verbose_name="Doyen"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Faculté"
        verbose_name_plural = "Facultés"
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(models.Model):
    """Département d'une faculté."""
    name = models.CharField(max_length=200, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='departments',
        verbose_name="Faculté"
    )
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='department_head',
        limit_choices_to={'role__in': ['TEACHER', 'DEAN']},
        verbose_name="Chef de département"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Département"
        verbose_name_plural = "Départements"
        ordering = ['faculty', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Level(models.Model):
    """Niveau d'études (L1, L2, L3, M1, M2, etc.)."""

    class LevelType(models.TextChoices):
        L1 = 'L1', 'Licence 1'
        L2 = 'L2', 'Licence 2'
        L3 = 'L3', 'Licence 3'
        M1 = 'M1', 'Master 1'
        M2 = 'M2', 'Master 2'
        D1 = 'D1', 'Doctorat 1'
        D2 = 'D2', 'Doctorat 2'
        D3 = 'D3', 'Doctorat 3'

    name = models.CharField(
        max_length=2,
        choices=LevelType.choices,
        unique=True,
        verbose_name="Niveau"
    )
    order = models.PositiveIntegerField(verbose_name="Ordre")

    class Meta:
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"
        ordering = ['order']

    def __str__(self):
        return self.get_name_display()


class Program(models.Model):
    """Programme/Filière d'études."""
    name = models.CharField(max_length=200, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='programs',
        verbose_name="Département"
    )
    levels = models.ManyToManyField(
        Level,
        related_name='programs',
        verbose_name="Niveaux"
    )
    duration_years = models.PositiveIntegerField(default=1, verbose_name="Durée (années)")
    description = models.TextField(blank=True, verbose_name="Description")
    tuition_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Frais de scolarité"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Programme"
        verbose_name_plural = "Programmes"
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Classroom(models.Model):
    """Salle de classe."""
    name = models.CharField(max_length=100, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    building = models.CharField(max_length=100, blank=True, verbose_name="Bâtiment")
    capacity = models.PositiveIntegerField(default=30, verbose_name="Capacité")
    has_projector = models.BooleanField(default=False, verbose_name="Projecteur")
    has_computers = models.BooleanField(default=False, verbose_name="Ordinateurs")
    is_available = models.BooleanField(default=True, verbose_name="Disponible")

    class Meta:
        verbose_name = "Salle de classe"
        verbose_name_plural = "Salles de classe"
        ordering = ['building', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"
