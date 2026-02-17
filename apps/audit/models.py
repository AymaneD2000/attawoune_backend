from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'CREATE', _('Création')
        UPDATE = 'UPDATE', _('Modification')
        DELETE = 'DELETE', _('Suppression')
        LOGIN = 'LOGIN', _('Connexion')
        LOGOUT = 'LOGOUT', _('Déconnexion')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('Utilisateur')
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_('Action')
    )
    model_name = models.CharField(max_length=100, verbose_name=_('Modèle'))
    object_id = models.CharField(max_length=100, verbose_name=_('ID Objet'))
    object_repr = models.CharField(max_length=255, verbose_name=_('Représentation'))
    details = models.JSONField(default=dict, blank=True, verbose_name=_('Détails'))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('Adresse IP'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Date et heure'))

    class Meta:
        verbose_name = _('Journal d\'audit')
        verbose_name_plural = _('Journaux d\'audit')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} {self.model_name} ({self.timestamp})"
