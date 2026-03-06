"""
Administration ViewSets.

Now handles two separate review queues:
  - StudentProfileViewSet   → /api/v1/admin/students/
  - PersonalProfileViewSet  → /api/v1/admin/personal/
  - UserManagementViewSet   → /api/v1/admin/users/

Both profile viewsets share identical approve/reject action logic —
the only difference is which model and list serializer they use.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.kyc.models import PersonalProfile, StudentProfile
from apps.kyc.serializers import (
    PersonalProfileReadSerializer,
    StudentProfileReadSerializer,
)
from apps.users.models import User
from apps.users.serializers import UserProfileSerializer

from .permissions import CanReviewApplications, IsStaffUser
from .serializers import (
    ApproveApplicationSerializer,
    PersonalProfileListSerializer,
    ReactivateUserSerializer,
    RejectApplicationSerializer,
    StudentProfileListSerializer,
    SuspendUserSerializer,
)


# ── Shared mixin ──────────────────────────────────────────────────────────────

class ReviewActionsMixin:
    """
    Provides approve() and reject() actions for any profile ViewSet.

    Both StudentProfileViewSet and PersonalProfileViewSet inherit this.
    The mixin reads self.get_object() which works correctly because
    each ViewSet sets its own queryset.

    This avoids duplicating 40 lines of identical action code.
    """

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[CanReviewApplications],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        profile = self.get_object()

        serializer = ApproveApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=profile, reviewed_by=request.user)

        # Return the full detail serializer so the frontend
        # gets the updated profile state in the same response
        read_serializer = self.get_serializer(profile)
        return Response(
            {
                "detail": f"Application for '{profile.user.get_full_name()}' has been approved.",
                "profile": read_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[CanReviewApplications],
        url_path="reject",
    )
    def reject(self, request, pk=None):
        profile = self.get_object()

        serializer = RejectApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=profile, reviewed_by=request.user)

        return Response(
            {
                "detail": f"Application for '{profile.user.get_full_name()}' has been rejected.",
            },
            status=status.HTTP_200_OK,
        )


# ── Student review ViewSet ────────────────────────────────────────────────────

class StudentProfileViewSet(ReviewActionsMixin, viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/v1/admin/students/               → review queue
    GET  /api/v1/admin/students/<id>/          → full detail with documents
    POST /api/v1/admin/students/<id>/approve/  → approve application
    POST /api/v1/admin/students/<id>/reject/   → reject application
    """

    permission_classes = [IsStaffUser, CanReviewApplications]

    queryset = (
        StudentProfile.objects
        .select_related("user", "reviewed_by")
        .prefetch_related("documents")
        .order_by("-created_at")
    )

    def get_serializer_class(self):
        if self.action == "list":
            return StudentProfileListSerializer
        return StudentProfileReadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search")
        if status_filter:
            qs = qs.filter(user__account_status=status_filter)
        if search:
            qs = qs.filter(
                user__email__icontains=search
            ) | qs.filter(
                user__first_name__icontains=search
            ) | qs.filter(
                user__last_name__icontains=search
            )
        return qs


# ── Personal account review ViewSet ──────────────────────────────────────────

class PersonalProfileViewSet(ReviewActionsMixin, viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/v1/admin/personal/               → review queue
    GET  /api/v1/admin/personal/<id>/          → full detail with documents
    POST /api/v1/admin/personal/<id>/approve/  → approve application
    POST /api/v1/admin/personal/<id>/reject/   → reject application
    """

    permission_classes = [IsStaffUser, CanReviewApplications]

    queryset = (
        PersonalProfile.objects
        .select_related("user", "reviewed_by")
        .prefetch_related("documents")
        .order_by("-created_at")
    )

    def get_serializer_class(self):
        if self.action == "list":
            return PersonalProfileListSerializer
        return PersonalProfileReadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search")
        if status_filter:
            qs = qs.filter(user__account_status=status_filter)
        if search:
            qs = qs.filter(
                user__email__icontains=search
            ) | qs.filter(
                user__first_name__icontains=search
            ) | qs.filter(
                user__last_name__icontains=search
            )
        return qs


# ── User management ViewSet ───────────────────────────────────────────────────

class UserManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/v1/admin/users/                  → all users
    GET  /api/v1/admin/users/<id>/             → user detail
    POST /api/v1/admin/users/<id>/suspend/     → suspend account
    POST /api/v1/admin/users/<id>/reactivate/  → reactivate account
    """

    permission_classes = [IsStaffUser]
    serializer_class = UserProfileSerializer

    queryset = (
        User.objects
        .select_related("role")
        .order_by("-date_joined")
    )

    def get_queryset(self):
        qs = super().get_queryset()
        role_filter = self.request.query_params.get("role")
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        if role_filter:
            qs = qs.filter(role__slug=role_filter)
        if status_filter:
            qs = qs.filter(account_status=status_filter)
        if search:
            qs = qs.filter(email__icontains=search)

        return qs

    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request, pk=None):
        user = self.get_object()
        serializer = SuspendUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, actioned_by=request.user)
        return Response(
            {"detail": f"Account for '{user.email}' has been suspended."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request, pk=None):
        user = self.get_object()
        serializer = ReactivateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, actioned_by=request.user)
        return Response(
            {"detail": f"Account for '{user.email}' has been reactivated."},
            status=status.HTTP_200_OK,
        )