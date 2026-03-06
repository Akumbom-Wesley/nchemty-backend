from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    LogoutView,
    MeAuthView,
    ResendOTPView,
)
from .password_reset import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
)

app_name = "authentication"

urlpatterns = [
    # ── Login flow ─────────────────────────────────────────────────────
    path("login/", LoginView.as_view(), name="login"),

    # ── 2FA verify — dormant, uncomment when 2FA re-enabled ───────────
    # path("login/verify-2fa/", TwoFAVerifyView.as_view(), name="verify-2fa"),

    # ── Session ────────────────────────────────────────────────────────
    path("me/", MeAuthView.as_view(), name="auth-me"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # ── OTP ────────────────────────────────────────────────────────────
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),

    # ── Password reset ─────────────────────────────────────────────────
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/verify/", PasswordResetVerifyView.as_view(), name="password-reset-verify"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]