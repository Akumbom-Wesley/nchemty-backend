from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Role
from .serializers import (
    ChangePasswordSerializer,
    RoleSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
)


class RoleListView(generics.ListAPIView):
    """
    GET /api/v1/users/roles/

    Public endpoint — the frontend needs this to build a dynamic
    registration form showing available roles.
    Only returns active roles.
    """

    serializer_class = RoleSerializer
    permission_classes = [AllowAny]
    queryset = Role.objects.filter(is_active=True)


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/users/me/  → returns the current user's profile
    PATCH /api/v1/users/me/ → updates allowed fields (full_name)

    Uses two different serializers for read vs write — this prevents
    accidentally exposing write fields in GET responses.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserProfileSerializer


class ChangePasswordView(APIView):
    """
    POST /api/v1/users/me/change-password/

    The serializer handles all validation and the save.
    This view just orchestrates request → serializer → response.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )