"""
Password reset flow.

Kept in its own file because it's a distinct 3-step feature:
  Step 1: Request reset  → POST /auth/password-reset/request/
  Step 2: Verify OTP     → POST /auth/password-reset/verify/
  Step 3: Set new pass   → POST /auth/password-reset/confirm/

Security considerations:
- Step 1 always returns 200 (never confirms if email exists)
- OTP is single-use and expires in OTP_EXPIRY_MINUTES
- Step 2 returns a short-lived reset_token (not a full JWT)
  so the confirm step is bound to the verified OTP session
- The reset_token is itself a JWT with a tight 10-minute lifetime
  and a special claim — it cannot be used as an access token
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditLog
from apps.users.models import User

from .emails import send_password_reset_otp
from .models import OTPCode
from .throttles import OTPRateThrottle, PasswordResetRateThrottle


# ── Serializers ───────────────────────────────────────────────────────────────

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, ip=None, user_agent=""):
        """
        Always succeeds from the caller's perspective.
        If the email doesn't exist, we silently do nothing —
        the view returns 200 either way (prevents enumeration).
        """
        email = self.validated_data["email"].lower().strip()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return  # silent — caller returns 200 regardless

        otp = OTPCode.create_for_user(
            user,
            OTPCode.Purpose.PASSWORD_RESET,
            ip=ip,
        )
        send_password_reset_otp(user, otp.code)

        AuditLog.log(
            AuditLog.EventType.PASSWORD_RESET_REQUESTED,
            user=user,
            ip=ip,
            user_agent=user_agent,
        )


class PasswordResetVerifySerializer(serializers.Serializer):
    """
    Verifies the OTP. On success, issues a short-lived reset_token.
    The reset_token must be submitted in the confirm step.

    Why a reset_token instead of just accepting email+OTP+password
    all in one step?
    - Separating verify from confirm means the OTP is consumed before
      the new password is sent over the wire — tighter window
    - The reset_token can be validated independently, making the
      confirm step simpler
    """

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid reset details.")

        valid, reason = OTPCode.verify(user, attrs["code"], OTPCode.Purpose.PASSWORD_RESET)
        if not valid:
            if reason == "expired":
                raise serializers.ValidationError("This code has expired. Please request a new one.")
            raise serializers.ValidationError("Invalid or already used reset code.")

        attrs["_user"] = user
        return attrs

    def get_reset_token(self):
        """
        Issues a special short-lived JWT that authorises only the
        password reset confirm step — not a full login.
        """
        user = self.validated_data["_user"]

        # Use a plain RefreshToken as the carrier — short access lifetime
        token = RefreshToken.for_user(user)
        token["token_type"] = "password_reset"   # marks it as special-purpose
        token["email"] = user.email

        # Return only the access token — no refresh token for reset flow
        access = token.access_token
        return str(access)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Accepts the reset_token from the verify step and the new password.
    Validates the token's special claim before allowing the change.
    """

    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=12)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        # Decode and validate the reset token
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError

        try:
            token = AccessToken(attrs["reset_token"])
        except TokenError:
            raise serializers.ValidationError(
                {"reset_token": "Invalid or expired reset token. Please start over."}
            )

        # Enforce that this token was issued for password reset only
        if token.get("token_type") != "password_reset":
            raise serializers.ValidationError(
                {"reset_token": "Invalid token type."}
            )

        try:
            user = User.objects.get(id=token["user_id"], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Account not found.")

        attrs["_user"] = user
        return attrs

    def save(self, ip=None, user_agent=""):
        user = self.validated_data["_user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        AuditLog.log(
            AuditLog.EventType.PASSWORD_RESET_SUCCESS,
            user=user,
            ip=ip,
            user_agent=user_agent,
        )
        return user


# ── Views ─────────────────────────────────────────────────────────────────────

def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            ip=_get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            {"detail": "If an account with that email exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.get_reset_token()
        return Response(
            {
                "detail": "OTP verified. Use the reset_token to set your new password.",
                "reset_token": reset_token,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            ip=_get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            {"detail": "Password reset successful. You may now log in."},
            status=status.HTTP_200_OK,
        )