from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
from .middleware import get_current_request, get_current_user
import json
from django.core.serializers.json import DjangoJSONEncoder

EXCLUDED_MODELS = ['AuditLog', 'Session', 'LogEntry', 'ContentType', 'Permission', 'Group']

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if sender.__name__ in EXCLUDED_MODELS:
        return

    request = get_current_request()
    user = get_current_user()
    
    # Even if no user (system action), we might want to log it if it's critical
    # For now, let's log everything where we have a request context or if needed
    
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    
    try:
        # Simple serialization of changed fields could be complex logic
        # For now, just store string representation
        details = {}
        if not created:
            # TODO: Implement field tracking if needed (requires pre_save signal to compare)
            pass
            
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            ip_address=get_client_ip(request) if request else None,
            details=details
        )
    except Exception as e:
        # Don't fail the main transaction if logging fails
        print(f"Audit Log Error: {e}")

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender.__name__ in EXCLUDED_MODELS:
        return

    request = get_current_request()
    user = get_current_user()

    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=AuditLog.Action.DELETE,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            ip_address=get_client_ip(request) if request else None,
            details={}
        )
    except Exception as e:
        print(f"Audit Log Error: {e}")
