from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with role-based access control."""

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        DEAN = 'DEAN', 'Doyen'
        TEACHER = 'TEACHER', 'Enseignant'
        STUDENT = 'STUDENT', 'Étudiant'
        ACCOUNTANT = 'ACCOUNTANT', 'Comptable'
        SECRETARY = 'SECRETARY', 'Secrétaire'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    verbose_name="Rôle"
    )

    class Gender(models.TextChoices):
        MALE = 'M', 'Homme'
        FEMALE = 'F', 'Femme'

    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        default=Gender.MALE,
        verbose_name="Sexe"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    address = models.TextField(blank=True, verbose_name="Adresse")
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_dean(self):
        return self.role == self.Role.DEAN
