"""
Audit log model.

Every security-sensitive action in the system writes a row here.
This table is append-only — no updates, no deletes. Ever.

Why a DB table and not just file logs?
- Queryable: "show me all login attempts for this IP in the last 24h"
- Survives log rotation
- Accessible to the admin UI without SSH access
- Can be exported for compliance reporting

Why not use Django's built-in LogEntry (admin audit)?
- LogEntry only captures admin panel actions
- We need to capture API actions, login attempts, OTP events
- We want structured fields (ip, user, event_type) not just text
"""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable record of a security-relevant event.

    Append-only by convention — nothing in the codebase ever calls
    .update() or .delete() on this model. In production, add a
    DB-level policy (e.g. PostgreSQL RLS) to enforce this at the
    infrastructure level.
    """

    class EventType(models.TextChoices):
        # Authentication events
        LOGIN_SUCCESS = "login_success", "Login Success"
        LOGIN_FAILED = "login_failed", "Login Failed"
        LOGIN_2FA_SUCCESS = "login_2fa_success", "2FA Login Success"
        LOGIN_2FA_FAILED = "login_2fa_failed", "2FA Login Failed"
        LOGOUT = "logout", "Logout"

        # Registration & verification
        REGISTER = "register", "Registration"
        REAPPLICATION = "reapplication", "Reapplication After Rejection"
        EMAIL_VERIFIED = "email_verified", "Email Verified"
        OTP_RESENT = "otp_resent", "OTP Resent"

        # Password
        PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password Reset Requested"
        PASSWORD_RESET_SUCCESS = "password_reset_success", "Password Reset Success"
        PASSWORD_CHANGED = "password_changed", "Password Changed"

        # Account state changes (admin actions)
        ACCOUNT_APPROVED = "account_approved", "Account Approved"
        ACCOUNT_REJECTED = "account_rejected", "Account Rejected"
        ACCOUNT_SUSPENDED = "account_suspended", "Account Suspended"
        ACCOUNT_REACTIVATED = "account_reactivated", "Account Reactivated"

        # Document events
        DOCUMENT_UPLOADED = "document_uploaded", "Document Uploaded"

        # Security events
        ACCOUNT_LOCKED = "account_locked", "Account Locked (Too Many Attempts)"
        SUSPICIOUS_REQUEST = "suspicious_request", "Suspicious Request Detected"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    # Who did it — nullable because some events (failed login with unknown
    # email) have no resolvable user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    # What happened
    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
    )

    # Where from
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.CharField(max_length=512, blank=True)

    # What exactly — freeform metadata (JSON)
    # Examples:
    #   login_failed: {"email": "x@y.com", "reason": "bad_password"}
    #   account_approved: {"approved_by": "admin@bank.cm", "association": "Red Cross Yaounde"}
    #   document_uploaded: {"document_type": "recepisse", "filename": "receipt.pdf"}
    metadata = models.JSONField(default=dict, blank=True)

    # Email of the subject even if user FK is null — for failed login logging
    email = models.EmailField(blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "audit"
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
            models.Index(fields=["email", "event_type"]),
        ]

    def __str__(self):
        who = self.email or (str(self.user) if self.user else "anonymous")
        return f"[{self.severity.upper()}] {self.event_type} — {who} @ {self.created_at:%Y-%m-%d %H:%M}"

    # ── Factory method ────────────────────────────────────────────────

    @classmethod
    def log(
        cls,
        event_type,
        *,
        user=None,
        email="",
        ip=None,
        user_agent="",
        metadata=None,
        severity=None,
    ):
        """
        The single call site for writing audit events.

        Usage:
            AuditLog.log(
                AuditLog.EventType.LOGIN_SUCCESS,
                user=user,
                ip=request_ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

        Severity defaults:
        - CRITICAL for locked/suspicious events
        - WARNING for failed events
        - INFO for everything else
        Auto-detected from event_type if not provided.
        """
        if severity is None:
            severity = cls._infer_severity(event_type)

        if user and not email:
            email = user.email

        cls.objects.create(
            user=user,
            event_type=event_type,
            severity=severity,
            ip_address=ip,
            user_agent=user_agent[:512],
            metadata=metadata or {},
            email=email,
        )

    @classmethod
    def _infer_severity(cls, event_type):
        if event_type in (
            cls.EventType.ACCOUNT_LOCKED,
            cls.EventType.SUSPICIOUS_REQUEST,
        ):
            return cls.Severity.CRITICAL

        if event_type in (
            cls.EventType.LOGIN_FAILED,
            cls.EventType.LOGIN_2FA_FAILED,
            cls.EventType.ACCOUNT_REJECTED,
            cls.EventType.ACCOUNT_SUSPENDED,
        ):
            return cls.Severity.WARNING

        return cls.Severity.INFO