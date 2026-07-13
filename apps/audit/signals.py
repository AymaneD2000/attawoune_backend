import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .middleware import get_current_request, get_current_user
from .models import AuditLog

logger = logging.getLogger(__name__)

AUDITED_APP_LABELS = {
    'accounts',
    'academics',
    'finance',
    'scheduling',
    'students',
    'teachers',
    'university',
}

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _should_audit(sender, raw=False):
    return (
        not raw
        and sender is not AuditLog
        and sender._meta.app_label in AUDITED_APP_LABELS
        and get_current_request() is not None
    )


def _schedule_audit_log(sender, instance, action):
    request = get_current_request()
    user = get_current_user()
    user_id = user.pk if user and user.is_authenticated else None
    payload = {
        'user_id': user_id,
        'action': action,
        'model_name': sender.__name__,
        'object_id': str(instance.pk),
        'object_repr': str(instance)[:255],
        'ip_address': get_client_ip(request),
        'details': {},
    }

    def write_log():
        try:
            AuditLog.objects.create(**payload)
        except Exception:
            # Auditing must never roll back the business transaction. This callback
            # runs after commit, so a missing/unavailable audit table cannot poison it.
            logger.exception('Unable to write audit log for %s', sender._meta.label)

    transaction.on_commit(write_log)

@receiver(post_save)
def audit_post_save(sender, instance, created, raw=False, **kwargs):
    if not _should_audit(sender, raw=raw):
        return
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    _schedule_audit_log(sender, instance, action)

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if not _should_audit(sender):
        return
    _schedule_audit_log(sender, instance, AuditLog.Action.DELETE)
