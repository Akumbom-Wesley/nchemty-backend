"""
Student registration and reapplication serializers.
"""

from django.db import transaction
from rest_framework import serializers

from apps.users.models import Role
from apps.kyc.models import StudentDocument, StudentProfile
from apps.kyc.validators import validate_document_file, validate_passport_photo

from .base import BaseRegistrationSerializer, BaseReapplySerializer
from ...authentication.emails import send_reapplication_confirmation


class StudentRegistrationSerializer(BaseRegistrationSerializer):

    doc_national_id = serializers.FileField()
    doc_location_plan = serializers.FileField()
    doc_passport_photo = serializers.FileField()

    DOCUMENT_FIELD_MAP = {
        "doc_national_id": (
            StudentDocument.DocumentType.NATIONAL_ID,
            validate_document_file,
        ),
        "doc_location_plan": (
            StudentDocument.DocumentType.LOCATION_PLAN,
            validate_document_file,
        ),
        "doc_passport_photo": (
            StudentDocument.DocumentType.PASSPORT_PHOTO,
            validate_passport_photo,
        ),
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self._validate_documents(attrs, self.DOCUMENT_FIELD_MAP)

    @transaction.atomic
    def save(self):
        try:
            role = Role.objects.get(slug="student")
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                "Student role is not configured. Contact support."
            )

        user = self._create_base_user(self.validated_data, role)
        profile = StudentProfile.objects.create(user=user)

        for field_name, (doc_type, _) in self.DOCUMENT_FIELD_MAP.items():
            file = self.validated_data[field_name]
            StudentDocument.objects.create(
                profile=profile,
                document_type=doc_type,
                file=file,
                original_filename=file.name,
            )

        return user


class StudentReapplySerializer(BaseReapplySerializer):

    doc_national_id = serializers.FileField()
    doc_location_plan = serializers.FileField()
    doc_passport_photo = serializers.FileField()

    DOCUMENT_FIELD_MAP = {
        "doc_national_id": (
            StudentDocument.DocumentType.NATIONAL_ID,
            validate_document_file,
        ),
        "doc_location_plan": (
            StudentDocument.DocumentType.LOCATION_PLAN,
            validate_document_file,
        ),
        "doc_passport_photo": (
            StudentDocument.DocumentType.PASSPORT_PHOTO,
            validate_passport_photo,
        ),
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self._validate_documents(attrs, self.DOCUMENT_FIELD_MAP)

    @transaction.atomic
    def save(self):
        from apps.audit.models import AuditLog

        user = self.validated_data["_user"]
        profile, _ = StudentProfile.objects.get_or_create(user=user)

        profile.documents.all().delete()

        for field_name, (doc_type, _) in self.DOCUMENT_FIELD_MAP.items():
            file = self.validated_data[field_name]
            StudentDocument.objects.create(
                profile=profile,
                document_type=doc_type,
                file=file,
                original_filename=file.name,
            )

        profile.admin_notes = ""
        profile.reviewed_by = None
        profile.reviewed_at = None
        profile.save(update_fields=["admin_notes", "reviewed_by", "reviewed_at"])

        self._reset_user_to_pending(user)

        AuditLog.log(
            AuditLog.EventType.REAPPLICATION,
            user=user,
            metadata={"role": "student"},
        )

        send_reapplication_confirmation(user)

        return user