from django.db import models
from django.conf import settings


class Teacher(models.Model):
    """Profil enseignant lié à un utilisateur."""

    class ContractType(models.TextChoices):
        PERMANENT = 'PERMANENT', 'Permanent'
        CONTRACT = 'CONTRACT', 'Contractuel'
        VISITING = 'VISITING', 'Vacataire'
        PART_TIME = 'PART_TIME', 'Temps partiel'

    class Rank(models.TextChoices):
        ASSISTANT = 'ASSISTANT', 'Assistant'
        LECTURER = 'LECTURER', 'Maître assistant'
        SENIOR_LECTURER = 'SENIOR_LECTURER', 'Maître de conférences'
        ASSOCIATE_PROFESSOR = 'ASSOCIATE_PROFESSOR', 'Professeur associé'
        PROFESSOR = 'PROFESSOR', 'Professeur'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        limit_choices_to={'role': 'TEACHER'},
        verbose_name="Utilisateur"
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Matricule"
    )
    department = models.ForeignKey(
        'university.Department',
        on_delete=models.SET_NULL,
        null=True,
        related_name='teachers',
        verbose_name="Département"
    )
    rank = models.CharField(
        max_length=30,
        choices=Rank.choices,
        default=Rank.ASSISTANT,
        verbose_name="Grade"
    )
    contract_type = models.CharField(
        max_length=20,
        choices=ContractType.choices,
        default=ContractType.PERMANENT,
        verbose_name="Type de contrat"
    )
    hire_date = models.DateField(verbose_name="Date d'embauche")
    specialization = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Spécialisation"
    )
    office_location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bureau"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Enseignant"
        verbose_name_plural = "Enseignants"
        ordering = ['employee_id']

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.generate_employee_id()
        super().save(*args, **kwargs)

    def generate_employee_id(self):
        """
        Génère un matricule au format: ENS[YY][YY+1][Initial][SEQ]
        Exemple: ENS1920A001
        """
        # Prefix
        prefix_base = "ENS"
        
        # Year
        from django.utils import timezone
        date = self.hire_date or timezone.now().date()
        year = date.year
        yy = year % 100
        yy_next = (yy + 1) % 100
        year_str = f"{yy:02d}{yy_next:02d}"
        
        # Initial
        initial = self.user.first_name[0].upper() if self.user.first_name else 'X'
        
        prefix = f"{prefix_base}{year_str}{initial}"
        
        # Sequence
        last_teacher = Teacher.objects.filter(employee_id__startswith=prefix).order_by('-employee_id').first()
        
        if last_teacher:
            try:
                last_seq = int(last_teacher.employee_id[-3:])
                new_seq = last_seq + 1
            except ValueError:
                new_seq = 1
        else:
            new_seq = 1
            
        self.employee_id = f"{prefix}{new_seq:03d}"

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


class TeacherCourse(models.Model):
    """Affectation d'un enseignant à un cours pour un semestre."""
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='course_assignments',
        verbose_name="Enseignant"
    )
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
        verbose_name="Cours"
    )
    semester = models.ForeignKey(
        'university.Semester',
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
        verbose_name="Semestre"
    )
    is_primary = models.BooleanField(
        default=True,
        verbose_name="Enseignant principal"
    )
    assigned_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Affectation cours"
        verbose_name_plural = "Affectations cours"
        unique_together = ['teacher', 'course', 'semester']

    def __str__(self):
        return f"{self.teacher} - {self.course} ({self.semester})"


class TeacherContract(models.Model):
    """Contrat d'un enseignant."""

    class ContractStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        EXPIRED = 'EXPIRED', 'Expiré'
        TERMINATED = 'TERMINATED', 'Résilié'
        RENEWED = 'RENEWED', 'Renouvelé'

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name="Enseignant"
    )
    contract_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de contrat"
    )
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin"
    )
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Salaire de base"
    )
    status = models.CharField(
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.ACTIVE,
        verbose_name="Statut"
    )
    document = models.FileField(
        upload_to='contracts/',
        blank=True,
        null=True,
        verbose_name="Document"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contrat"
        verbose_name_plural = "Contrats"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.contract_number} - {self.teacher}"
