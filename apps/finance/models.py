from django.db import models
from django.conf import settings
from decimal import Decimal


class TuitionPayment(models.Model):
    """Paiement des frais de scolarité."""

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Espèces'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Virement bancaire'
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
        CHECK = 'CHECK', 'Chèque'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        COMPLETED = 'COMPLETED', 'Complété'
        FAILED = 'FAILED', 'Échoué'
        REFUNDED = 'REFUNDED', 'Remboursé'

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='tuition_payments',
        verbose_name="Étudiant"
    )
    academic_year = models.ForeignKey(
        'university.AcademicYear',
        on_delete=models.PROTECT,
        related_name='tuition_payments',
        verbose_name="Année académique"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Méthode de paiement"
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="Statut"
    )
    reference = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Référence"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro de reçu"
    )
    payment_date = models.DateField(verbose_name="Date de paiement")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_payments',
        verbose_name="Reçu par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paiement de scolarité"
        verbose_name_plural = "Paiements de scolarité"
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.reference} - {self.student} ({self.amount})"


class TuitionFee(models.Model):
    """Configuration des frais de scolarité par programme et année."""
    program = models.ForeignKey(
        'university.Program',
        on_delete=models.CASCADE,
        related_name='tuition_fees',
        verbose_name="Programme"
    )
    academic_year = models.ForeignKey(
        'university.AcademicYear',
        on_delete=models.CASCADE,
        related_name='tuition_fees',
        verbose_name="Année académique"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant"
    )
    installments_allowed = models.PositiveIntegerField(
        default=1,
        verbose_name="Nombre de tranches"
    )
    due_date = models.DateField(verbose_name="Date limite")

    class Meta:
        verbose_name = "Frais de scolarité"
        verbose_name_plural = "Frais de scolarité"
        unique_together = ['program', 'academic_year']

    def __str__(self):
        return f"{self.program} - {self.academic_year}: {self.amount}"


class StudentBalance(models.Model):
    """Solde financier d'un étudiant pour une année académique."""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='balances',
        verbose_name="Étudiant"
    )
    academic_year = models.ForeignKey(
        'university.AcademicYear',
        on_delete=models.CASCADE,
        related_name='student_balances',
        verbose_name="Année académique"
    )
    total_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total dû"
    )
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total payé"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Solde étudiant"
        verbose_name_plural = "Soldes étudiants"
        unique_together = ['student', 'academic_year']

    def __str__(self):
        return f"{self.student} - {self.academic_year}: {self.balance}"

    @property
    def balance(self):
        return self.total_due - self.total_paid

    @property
    def is_paid(self):
        return self.total_paid >= self.total_due


class Salary(models.Model):
    """Salaire d'un employé (enseignant ou administrateur)."""

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        PAID = 'PAID', 'Payé'
        CANCELLED = 'CANCELLED', 'Annulé'

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='salaries',
        verbose_name="Employé"
    )
    month = models.PositiveIntegerField(verbose_name="Mois")
    year = models.PositiveIntegerField(verbose_name="Année")
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Salaire de base"
    )
    bonuses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Primes"
    )
    deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Déductions"
    )
    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Salaire net"
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="Statut"
    )
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )
    remarks = models.TextField(blank=True, verbose_name="Remarques")
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_salaries',
        verbose_name="Traité par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salaire"
        verbose_name_plural = "Salaires"
        unique_together = ['employee', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year}: {self.net_salary}"

    def save(self, *args, **kwargs):
        self.net_salary = self.base_salary + self.bonuses - self.deductions
        super().save(*args, **kwargs)


class Expense(models.Model):
    """Dépenses de l'université."""

    class ExpenseCategory(models.TextChoices):
        SALARIES = 'SALARIES', 'Salaires'
        UTILITIES = 'UTILITIES', 'Services publics'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        EQUIPMENT = 'EQUIPMENT', 'Équipement'
        SUPPLIES = 'SUPPLIES', 'Fournitures'
        OTHER = 'OTHER', 'Autres'

    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        verbose_name="Catégorie"
    )
    description = models.TextField(verbose_name="Description")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant"
    )
    date = models.DateField(verbose_name="Date")
    receipt = models.FileField(
        upload_to='expenses/',
        blank=True,
        null=True,
        verbose_name="Reçu"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_expenses',
        verbose_name="Approuvé par"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_expenses',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ['-date']

    def __str__(self):
        return f"{self.get_category_display()} - {self.amount} ({self.date})"
