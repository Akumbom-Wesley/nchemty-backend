from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Applied to the login endpoint.
    5 attempts per minute per IP — complements django-axes which
    locks at 5 failed attempts over a longer window.
    Both layers working together: axes handles account lockout,
    this handles burst-rate abuse from a single IP.
    """
    scope = "login"


class OTPRateThrottle(AnonRateThrottle):
    """
    Applied to OTP submission endpoints (email verify + 2FA verify).
    Prevents automated OTP brute-forcing.
    5 attempts per minute per IP.
    """
    scope = "otp"


class RegistrationRateThrottle(AnonRateThrottle):
    """
    Applied to registration endpoints.
    Prevents mass account creation from a single IP.
    10 attempts per minute is generous for real users,
    prohibitive for bots.
    """
    scope = "registration"


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Applied to password reset request.
    Prevents using the reset flow to enumerate valid emails
    (timing + volume attacks).
    """
    scope = "password_reset"