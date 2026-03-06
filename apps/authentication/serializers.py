"""
Authentication serializers.

Registration has moved to apps/kyc — this file now handles
only the login flow, OTP verification, logout, and password reset.

2FA is commented out throughout — the branching logic is preserved
so it can be re-enabled by uncommenting when needed.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.audit.models import AuditLog

from .emails import send_2fa_otp, send_email_verification_otp
from .models import OTPCode
from .tokens import build_auth_response


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    """
    Validates email + password credentials.

    2FA branching is commented out — all successful logins
    issue tokens directly regardless of role config.
    To re-enable 2FA, uncomment the block in get_auth_response().
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        password = attrs["password"]
        request = self.context["request"]

        user = authenticate(request=request, username=email, password=password)

        if user is None:
            AuditLog.log(
                AuditLog.EventType.LOGIN_FAILED,
                email=email,
                ip=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"reason": "invalid_credentials"},
            )
            raise serializers.ValidationError(
                "Unable to log in with the provided credentials."
            )

        if not user.is_active:
            if user.is_pending:
                raise serializers.ValidationError(
                    "Your account is pending admin approval. "
                    "You will be notified by email once reviewed."
                )
            raise serializers.ValidationError(
                "Your account is not active. Please contact support."
            )

        attrs["_user"] = user
        return attrs

    def get_auth_response(self):
        user = self.validated_data["_user"]
        request = self.context["request"]

        AuditLog.log(
            AuditLog.EventType.LOGIN_SUCCESS,
            user=user,
            ip=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # ── 2FA disabled — uncomment to re-enable ──────────────
        # config = user.get_auth_config()
        # if config.get("requires_2fa") and config.get("2fa_method") == "email_otp":
        #     ip = _get_client_ip(request)
        #     otp = OTPCode.create_for_user(user, OTPCode.Purpose.TWO_FA_LOGIN, ip=ip)
        #     send_2fa_otp(user, otp.code)
        #     return {
        #         "status": "2fa_required",
        #         "detail": "A verification code has been sent to your email.",
        #         "email": user.email,
        #     }
        # ──────────────────────────────────────────────────────

        return build_auth_response(user)


# ── 2FA verify — kept but dormant ─────────────────────────────────────────────

class TwoFAVerifySerializer(serializers.Serializer):
    """
    Kept for when 2FA is re-enabled.
    Not wired to any active URL currently.
    """

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid verification details.")

        valid, reason = OTPCode.verify(user, attrs["code"], OTPCode.Purpose.TWO_FA_LOGIN)

        if not valid:
            if reason == "expired":
                raise serializers.ValidationError(
                    "This code has expired. Please log in again."
                )
            raise serializers.ValidationError("Invalid or already used code.")

        attrs["_user"] = user
        return attrs

    def get_token_response(self):
        user = self.validated_data["_user"]
        AuditLog.log(AuditLog.EventType.LOGIN_2FA_SUCCESS, user=user)
        return build_auth_response(user)


# ── Logout ────────────────────────────────────────────────────────────────────

class LogoutSerializer(serializers.Serializer):
    """
    Blacklists the submitted refresh token.
    """

    refresh = serializers.CharField()

    def save(self):
        try:
            token = RefreshToken(self.validated_data["refresh"])
            token.blacklist()
        except Exception:
            # Already invalid or blacklisted — treat as success
            pass


# ── Resend OTP ────────────────────────────────────────────────────────────────

class ResendOTPSerializer(serializers.Serializer):
    """
    Resends an OTP for email verification or 2FA.
    Always returns 200 regardless of whether the email exists
    to prevent email enumeration.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower().strip()
        try:
            self._user = User.objects.get(email=value)
        except User.DoesNotExist:
            self._user = None
        return value

    def save(self):
        user = getattr(self, "_user", None)
        if user is None:
            return None

        if user.is_verified:
            otp = OTPCode.create_for_user(user, OTPCode.Purpose.TWO_FA_LOGIN)
            send_2fa_otp(user, otp.code)
        elif user.is_pending:
            otp = OTPCode.create_for_user(user, OTPCode.Purpose.EMAIL_VERIFICATION)
            send_email_verification_otp(user, otp.code)

        return None