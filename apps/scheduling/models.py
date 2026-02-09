from django.db import models
from django.conf import settings


class TimeSlot(models.Model):
    """Créneau horaire."""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Lundi'
        TUESDAY = 1, 'Mardi'
        WEDNESDAY = 2, 'Mercredi'
        THURSDAY = 3, 'Jeudi'
        FRIDAY = 4, 'Vendredi'
        SATURDAY = 5, 'Samedi'
        SUNDAY = 6, 'Dimanche'

    day = models.IntegerField(
        choices=DayOfWeek.choices,
        verbose_name="Jour"
    )
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")

    class Meta:
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"
        ordering = ['day', 'start_time']
        unique_together = ['day', 'start_time', 'end_time']

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time}-{self.end_time}"


class Schedule(models.Model):
    """Emploi du temps pour un cours."""
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Cours"
    )
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Enseignant"
    )
    semester = models.ForeignKey(
        'university.Semester',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Semestre"
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Créneau"
    )
    classroom = models.ForeignKey(
        'university.Classroom',
        on_delete=models.SET_NULL,
        null=True,
        related_name='schedules',
        verbose_name="Salle"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Emploi du temps"
        verbose_name_plural = "Emplois du temps"
        ordering = ['semester', 'time_slot']

    def __str__(self):
        return f"{self.course} - {self.time_slot} ({self.classroom})"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Check for teacher conflicts
        conflicts = Schedule.objects.filter(
            teacher=self.teacher,
            semester=self.semester,
            time_slot=self.time_slot,
            is_active=True
        ).exclude(pk=self.pk)
        if conflicts.exists():
            raise ValidationError("L'enseignant a déjà un cours à ce créneau.")

        # Check for classroom conflicts
        if self.classroom:
            room_conflicts = Schedule.objects.filter(
                classroom=self.classroom,
                semester=self.semester,
                time_slot=self.time_slot,
                is_active=True
            ).exclude(pk=self.pk)
            if room_conflicts.exists():
                raise ValidationError("La salle est déjà occupée à ce créneau.")


class CourseSession(models.Model):
    """Séance de cours spécifique (pour la présence)."""

    class SessionType(models.TextChoices):
        LECTURE = 'LECTURE', 'Cours magistral'
        TUTORIAL = 'TUTORIAL', 'TD'
        PRACTICAL = 'PRACTICAL', 'TP'
        EXAM = 'EXAM', 'Examen'

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Emploi du temps"
    )
    date = models.DateField(verbose_name="Date")
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.LECTURE,
        verbose_name="Type de séance"
    )
    topic = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sujet"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    is_cancelled = models.BooleanField(default=False, verbose_name="Annulé")
    cancellation_reason = models.TextField(
        blank=True,
        verbose_name="Raison d'annulation"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Séance de cours"
        verbose_name_plural = "Séances de cours"
        ordering = ['-date']
        unique_together = ['schedule', 'date']

    def __str__(self):
        return f"{self.schedule.course} - {self.date}"


class Announcement(models.Model):
    """Annonce/Notification."""

    class AnnouncementType(models.TextChoices):
        GENERAL = 'GENERAL', 'Général'
        ACADEMIC = 'ACADEMIC', 'Académique'
        FINANCIAL = 'FINANCIAL', 'Financier'
        EXAM = 'EXAM', 'Examens'
        EVENT = 'EVENT', 'Événement'

    class TargetAudience(models.TextChoices):
        ALL = 'ALL', 'Tous'
        STUDENTS = 'STUDENTS', 'Étudiants'
        TEACHERS = 'TEACHERS', 'Enseignants'
        STAFF = 'STAFF', 'Personnel'

    title = models.CharField(max_length=200, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu")
    announcement_type = models.CharField(
        max_length=20,
        choices=AnnouncementType.choices,
        default=AnnouncementType.GENERAL,
        verbose_name="Type"
    )
    target_audience = models.CharField(
        max_length=20,
        choices=TargetAudience.choices,
        default=TargetAudience.ALL,
        verbose_name="Public cible"
    )
    faculty = models.ForeignKey(
        'university.Faculty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name="Faculté"
    )
    program = models.ForeignKey(
        'university.Program',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name="Programme"
    )
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    publish_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de publication"
    )
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'expiration"
    )
    is_pinned = models.BooleanField(default=False, verbose_name="Épinglé")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='announcements',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title
