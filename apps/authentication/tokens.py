"""
Custom JWT token classes.

Why a custom token class instead of using RefreshToken directly?

1. Centralised claim definition — every place that issues a token
   calls the same class, so claims are never inconsistent between
   registration, login, and token refresh flows.

2. Explicit over implicit — the claims we embed are documented and
   intentional. No surprise data leaking into tokens.

3. Testable — we can unit test token contents independently of views.

Token anatomy reminder:
  Header.Payload.Signature
  Payload contains our claims — readable by the frontend (base64 decoded),
  but the signature ensures they cannot be tampered with.

What we put in the token:
  - user_id      → so backend can identify user without a DB hit on every request
  - email        → convenience for frontend display
  - role         → frontend uses this to gate UI features
  - account_status → frontend can show "pending" state without an extra API call
  - is_staff     → frontend needs this to show/hide admin UI

What we deliberately DO NOT put in the token:
  - full_name, phone, address → PII that doesn't need to be in every request
  - is_superuser → no frontend use case; reduces attack surface
  - password hash → obviously never
  - document details → sensitive, belongs only in authenticated API responses
"""

from rest_framework_simplejwt.tokens import RefreshToken


class AuthToken(RefreshToken):
    """
    Custom refresh token that embeds role-aware claims.

    Usage:
        token = AuthToken.for_user(user)
        access = str(token.access_token)
        refresh = str(token)

    This replaces all direct RefreshToken.for_user() calls in serializers.py.
    """

    @classmethod
    def for_user(cls, user):
        """
        Overrides the serializers method to inject our custom claims
        into both the refresh token and its derived access token.
        """
        token = super().for_user(user)

        # Identity
        token["email"] = user.email

        # Role — None-safe: a superuser created via createsuperuser has no role
        token["role"] = user.role.slug if user.role else None
        token["role_name"] = user.role.name if user.role else None

        # Account state — frontend uses this to show "pending approval" UI
        token["account_status"] = user.account_status

        # Staff flag — gates admin UI on the frontend
        token["is_staff"] = user.is_staff

        return token


def get_tokens_for_user(user) -> dict:
    """
    Public helper function — the single call site for issuing tokens.

    All serializers that need to issue tokens call this function.
    If we ever switch from simplejwt to another library, we change
    this one function, not every serializer that issues tokens.

    Returns a dict ready to be sent as a JSON response.
    """
    token = AuthToken.for_user(user)

    return {
        "access": str(token.access_token),
        "refresh": str(token),
    }


def build_auth_response(user) -> dict:
    """
    Builds the full authenticated response payload.
    Called by LoginSerializer and TwoFAVerifySerializer after
    successful authentication.

    Centralising this here means the response shape is always
    consistent — no risk of the login flow and 2FA flow returning
    different structures.
    """
    tokens = get_tokens_for_user(user)

    return {
        "status": "authenticated",
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.get_full_name(),
            "role": user.role.slug if user.role else None,
            "account_status": user.account_status,
            "is_staff": user.is_staff,
        },
    }