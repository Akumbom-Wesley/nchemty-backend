"""
Audit signals.

Django signals decouple the "thing happened" from "record that it happened."
The User model's activate() method doesn't need to know about AuditLog.
The signal handler observes account_status changes and logs them.

Signal handlers are registered in AuditConfig.ready() — the AppConfig
is the correct place for this, not models.py or apps.py top-level,
because ready() is called after all models are loaded.

Signals used:
- post_save on User  → detect status transitions
- axes_user_locked   → log lockout events from django-axes
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("security")


def register_signals():
    """
    Called from AuditConfig.ready().
    Importing here avoids circular imports at module load time.
    """
    from apps.users.models import User
    from .models import AuditLog

    @receiver(post_save, sender=User, dispatch_uid="audit_user_status_change")
    def on_user_saved(sender, instance, created, **kwargs):
        """
        Fires after every User.save().
        We use update_fields to detect what changed — only log when
        account_status or is_active is part of the save.
        """
        update_fields = kwargs.get("update_fields") or set()

        # Convert frozenset to set for reliable membership testing
        update_fields = set(update_fields)

        if created:
            AuditLog.log(
                AuditLog.EventType.REGISTER,
                user=instance,
                metadata={"role": instance.role.slug if instance.role else None},
            )
            return

        # Only log status changes, not every profile update
        if "account_status" not in update_fields and "is_active" not in update_fields:
            return

        status = instance.account_status

        event_map = {
            "active": AuditLog.EventType.ACCOUNT_APPROVED,
            "suspended": AuditLog.EventType.ACCOUNT_SUSPENDED,
            "rejected": AuditLog.EventType.ACCOUNT_REJECTED,
        }

        event_type = event_map.get(status)
        if event_type:
            AuditLog.log(
                event_type,
                user=instance,
                metadata={"new_status": status},
            )

    # Hook into django-axes lockout signal
    try:
        from axes.signals import user_locked_out

        @receiver(user_locked_out, dispatch_uid="audit_axes_lockout")
        def on_account_locked(sender, request, username, ip_address, **kwargs):
            from .models import AuditLog
            AuditLog.log(
                AuditLog.EventType.ACCOUNT_LOCKED,
                email=username or "",
                ip=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"username_attempted": username},
            )
            logger.warning(
                "Account locked out",
                extra={"ip": ip_address, "username": username},
            )

    except ImportError:
        # axes not installed — skip gracefully
        pass