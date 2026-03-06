"""
Administration serializers.

Updated to handle both StudentProfile and PersonalProfile reviews.
The approve/reject logic is identical for both — the difference is
which profile model and email function is used.
"""

from django.utils import timezone
from rest_framework import serializers

from apps.audit.models import AuditLog
from apps.kyc.models import PersonalProfile, StudentProfile
from apps.kyc.serializers import (
    PersonalProfileReadSerializer,
    StudentProfileReadSerializer,
)
from apps.users.models import User
from apps.users.serializers import UserProfileSerializer


# ── Shared approval/rejection logic ──────────────────────────────────────────

class ApproveApplicationSerializer(serializers.Serializer):
    """
    Approves any KYC application — student or personal.
    The profile object is passed in at save() time so this
    serializer works for both profile types without changes.
    """

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )

    def save(self, profile, reviewed_by):
        from apps.authentication.emails import send_association_status_email

        if profile.user.is_verified:
            raise serializers.ValidationError(
                "This application is already approved."
            )

        if not profile.has_all_required_documents():
            raise serializers.ValidationError(
                "Cannot approve — applicant has not submitted all required documents."
            )

        profile.admin_notes = self.validated_data.get("notes", "")
        profile.reviewed_by = reviewed_by
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=["admin_notes", "reviewed_by", "reviewed_at"])

        profile.user.activate()

        send_association_status_email(profile.user, status="approved")

        AuditLog.log(
            AuditLog.EventType.ACCOUNT_APPROVED,
            user=profile.user,
            metadata={
                "approved_by": reviewed_by.email,
                "role": profile.user.role.slug if profile.user.role else None,
            },
        )
        return profile


class RejectApplicationSerializer(serializers.Serializer):
    """
    Rejects any KYC application — student or personal.
    Reason is required for accountability.
    """

    reason = serializers.CharField(max_length=1000)
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )

    def save(self, profile, reviewed_by):
        from apps.authentication.emails import send_association_status_email

        if profile.user.account_status == profile.user.AccountStatus.REJECTED:
            raise serializers.ValidationError(
                "This application has already been rejected."
            )

        reason = self.validated_data["reason"]
        internal_note = self.validated_data.get("notes", "")

        full_notes = f"REJECTION REASON: {reason}"
        if internal_note:
            full_notes += f"\n\nINTERNAL NOTES: {internal_note}"

        profile.admin_notes = full_notes
        profile.reviewed_by = reviewed_by
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=["admin_notes", "reviewed_by", "reviewed_at"])

        profile.user.reject()

        send_association_status_email(
            profile.user, status="rejected", reason=reason
        )

        AuditLog.log(
            AuditLog.EventType.ACCOUNT_REJECTED,
            user=profile.user,
            metadata={
                "rejected_by": reviewed_by.email,
                "reason": reason,
                "role": profile.user.role.slug if profile.user.role else None,
            },
        )
        return profile


# ── User management ───────────────────────────────────────────────────────────

class SuspendUserSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)

    def save(self, user, actioned_by):
        if not user.is_active:
            raise serializers.ValidationError(
                "This account is already inactive."
            )
        if user.is_staff:
            raise serializers.ValidationError(
                "Staff accounts cannot be suspended via the API."
            )

        user.suspend()

        AuditLog.log(
            AuditLog.EventType.ACCOUNT_SUSPENDED,
            user=user,
            metadata={
                "reason": self.validated_data["reason"],
                "actioned_by": actioned_by.email,
            },
        )
        return user


class ReactivateUserSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )

    def save(self, user, actioned_by):
        if user.is_active:
            raise serializers.ValidationError(
                "This account is already active."
            )
        if user.account_status == user.AccountStatus.REJECTED:
            raise serializers.ValidationError(
                "Rejected accounts cannot be reactivated. "
                "The applicant must submit a new application."
            )

        user.activate()

        AuditLog.log(
            AuditLog.EventType.ACCOUNT_REACTIVATED,
            user=user,
            metadata={"actioned_by": actioned_by.email},
        )
        return user


# ── List serializers ──────────────────────────────────────────────────────────

class StudentProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the student review queue."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(
        source="user.get_full_name", read_only=True
    )
    user_phone = serializers.CharField(
        source="user.phone_number", read_only=True
    )
    account_status = serializers.CharField(
        source="user.account_status", read_only=True
    )
    account_status_display = serializers.CharField(
        source="user.get_account_status_display", read_only=True
    )
    has_all_required_documents = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "user_email", "user_full_name", "user_phone",
            "account_status", "account_status_display",
            "has_all_required_documents", "created_at", "reviewed_at",
        ]


class PersonalProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the personal account review queue."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(
        source="user.get_full_name", read_only=True
    )
    user_phone = serializers.CharField(
        source="user.phone_number", read_only=True
    )
    account_status = serializers.CharField(
        source="user.account_status", read_only=True
    )
    account_status_display = serializers.CharField(
        source="user.get_account_status_display", read_only=True
    )
    has_all_required_documents = serializers.BooleanField(read_only=True)

    class Meta:
        model = PersonalProfile
        fields = [
            "id", "user_email", "user_full_name", "user_phone",
            "niu", "account_status", "account_status_display",
            "has_all_required_documents", "created_at", "reviewed_at",
        ]