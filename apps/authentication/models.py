import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_otp_code():
    """
    Generates a cryptographically secure 6-digit numeric OTP.

    We use secrets.choice over random.randint — the secrets module
    is designed for security-sensitive tokens, random is not.
    """
    alphabet = string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


class OTPCode(models.Model):
    """
    A one-time password record tied to a user and a purpose.

    Reusable for:
      - "email_verification" : sent after registration to verify email
      - "2fa_login"          : sent mid-login for 2FA step
      - "password_reset"     : sent to authorize a password reset

    Design decisions:
    - One model, purpose field — no duplicated OTP logic across features.
    - is_used flag + expires_at enforce single-use and time-bounded validity.
    - We store the raw code (not hashed) because OTPs are short-lived and
      low-entropy hashing offers little benefit. The expiry + single-use
      flag is the primary security control. If you want to hash, use
      hmac.compare_digest on a SHA-256 of the code.
    """

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        TWO_FA_LOGIN = "2fa_login", "2FA Login"
        PASSWORD_RESET = "password_reset", "Password Reset"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otp_codes",
    )
    code = models.CharField(max_length=6, default=generate_otp_code)
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Track the IP that requested this OTP — useful for audit logs
    requested_from_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # This index makes verify lookups fast:
            # WHERE user_id=? AND purpose=? AND is_used=false
            models.Index(fields=["user", "purpose", "is_used"]),
        ]

    def __str__(self):
        return f"OTP({self.purpose}) for {self.user.email} — {'used' if self.is_used else 'pending'}"

    # ── Model-level logic ────────────────────────────────────────────

    @classmethod
    def create_for_user(cls, user, purpose, ip=None):
        """
        Factory method: invalidates any prior unused OTPs for this
        user+purpose, then creates a fresh one.

        Calling code should always use this method, never OTPCode.objects.create()
        directly — this ensures the invalidation step never gets skipped.
        """
        # Invalidate previous unused OTPs for same purpose
        cls.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True)

        expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)

        return cls.objects.create(
            user=user,
            purpose=purpose,
            expires_at=expires_at,
            requested_from_ip=ip,
        )

    @classmethod
    def verify(cls, user, code, purpose):
        """
        Validates a submitted OTP code.

        Returns (True, None) on success.
        Returns (False, reason_string) on failure.

        Keeping the reason strings internal — the view maps these
        to generic HTTP responses to avoid leaking info to attackers.
        """
        try:
            otp = cls.objects.get(
                user=user,
                code=code,
                purpose=purpose,
                is_used=False,
            )
        except cls.DoesNotExist:
            return False, "invalid"

        if timezone.now() > otp.expires_at:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            return False, "expired"

        # Mark as used immediately — prevents replay attacks
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        return True, None

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at