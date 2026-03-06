"""
Email sending functions for Nchemty.

Each function corresponds to one email event.
Templates live in apps/authentication/email_templates/.
Both HTML and plain text versions are sent for every email.

All functions are fire-and-forget from the caller's perspective —
they raise on failure so the caller can decide whether to retry
or log the error. In production, wrap these in Celery tasks.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


TEMPLATE_DIR = "authentication/email_templates"
OTP_EXPIRY_MINUTES = getattr(settings, "OTP_EXPIRY_MINUTES", 10)
FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", "Nchemty <noreply@nchemty.cm>")


def _send(subject: str, to: str, template_name: str, context: dict) -> None:
    """
    Core send function. Renders both HTML and plain text templates
    and sends a multipart email.

    template_name: base name without extension
    e.g. "otp_verification" renders:
        authentication/email_templates/otp_verification.txt
        authentication/email_templates/otp_verification.html
    """
    txt_template = f"{TEMPLATE_DIR}/{template_name}.txt"
    html_template = f"{TEMPLATE_DIR}/{template_name}.html"

    text_body = render_to_string(txt_template, context)
    html_body = render_to_string(html_template, context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=FROM_EMAIL,
        to=[to],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def send_email_verification_otp(user, otp_code: str) -> None:
    """
    Sent immediately after registration.
    Contains the 6-digit OTP for email verification.
    """
    _send(
        subject="Verify your Nchemty account",
        to=user.email,
        template_name="otp_verification",
        context={
            "first_name": user.first_name,
            "otp_code": otp_code,
            "expiry_minutes": OTP_EXPIRY_MINUTES,
        },
    )


def send_2fa_otp(user, otp_code: str) -> None:
    """
    Sent during login when 2FA is enabled.
    Currently dormant — 2FA is disabled.
    """
    _send(
        subject="Your Nchemty login verification code",
        to=user.email,
        template_name="otp_verification",
        context={
            "first_name": user.first_name,
            "otp_code": otp_code,
            "expiry_minutes": OTP_EXPIRY_MINUTES,
        },
    )


def send_password_reset_otp(user, otp_code: str) -> None:
    """
    Sent when user requests a password reset.
    """
    _send(
        subject="Reset your Nchemty password",
        to=user.email,
        template_name="password_reset",
        context={
            "first_name": user.first_name,
            "otp_code": otp_code,
            "expiry_minutes": OTP_EXPIRY_MINUTES,
        },
    )


def send_account_approved_email(user) -> None:
    """
    Sent when admin approves a KYC application.
    Sends both the approval notification and the welcome email.
    """
    approved_date = timezone.now().strftime("%B %d, %Y")
    role_display = user.role.name if user.role else "Account"

    context = {
        "first_name": user.first_name,
        "full_name": user.get_full_name(),
        "email": user.email,
        "role": role_display,
        "approved_date": approved_date,
    }

    # Approval notification
    _send(
        subject="Your Nchemty account has been approved",
        to=user.email,
        template_name="account_approved",
        context=context,
    )

    # Welcome email
    _send(
        subject="Welcome to Nchemty!",
        to=user.email,
        template_name="welcome",
        context=context,
    )


def send_account_rejected_email(user, reason: str) -> None:
    """
    Sent when admin rejects a KYC application.
    Includes the rejection reason so the user knows what to fix.
    """
    _send(
        subject="Update on your Nchemty account application",
        to=user.email,
        template_name="account_rejected",
        context={
            "first_name": user.first_name,
            "reason": reason,
        },
    )


def send_reapplication_confirmation(user) -> None:
    """
    Sent when a rejected user reapplies.
    Confirms receipt of new documents.
    """
    role_display = user.role.name if user.role else "Account"

    _send(
        subject="Nchemty — Reapplication received",
        to=user.email,
        template_name="reapplication_confirmation",
        context={
            "first_name": user.first_name,
            "email": user.email,
            "role": role_display,
            "submitted_date": timezone.now().strftime("%B %d, %Y at %H:%M"),
        },
    )


def send_association_status_email(user, status: str, reason: str = "") -> None:
    """
    Legacy compatibility function — called by administration/serializers.py.
    Routes to the correct email function based on status.
    """
    if status == "approved":
        send_account_approved_email(user)
    elif status == "rejected":
        send_account_rejected_email(user, reason=reason)