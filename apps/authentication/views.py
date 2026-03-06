"""
Authentication views.
Registration has moved to apps/kyc/views.py.
This file handles login, logout, token refresh, and /me.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    ResendOTPSerializer,
)
from .throttles import (
    LoginRateThrottle,
    OTPRateThrottle,
)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Validates credentials and issues JWT tokens directly.
    2FA step is commented out — re-enable in LoginSerializer
    when ready.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        response_data = serializer.get_auth_response()
        return Response(response_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    Blacklists the refresh token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )


class MeAuthView(APIView):
    """
    GET /api/v1/auth/me/

    Returns auth-relevant state for the current token holder.
    Used by the frontend on app load to bootstrap session state.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.get_full_name(),
                "phone_number": user.phone_number,
                "role": user.role.slug if user.role else None,
                "account_status": user.account_status,
                "is_verified": user.is_verified,
                "is_staff": user.is_staff,
            },
            status=status.HTTP_200_OK,
        )


class ResendOTPView(APIView):
    """
    POST /api/v1/auth/resend-otp/

    Always returns 200 — prevents email enumeration.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid()
        serializer.save()
        return Response(
            {"detail": "If an account with that email exists, a new code has been sent."},
            status=status.HTTP_200_OK,
        )