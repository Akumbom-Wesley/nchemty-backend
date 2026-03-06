"""
Personal account registration and reapplication serializers.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.users.models import Role
from apps.kyc.models import PersonalDocument, PersonalProfile
from apps.kyc.validators import validate_document_file

from .base import BaseRegistrationSerializer, BaseReapplySerializer
from ...authentication.emails import send_reapplication_confirmation


class PersonalRegistrationSerializer(BaseRegistrationSerializer):

    doc_location_plan = serializers.FileField()
    doc_niu = serializers.FileField(required=False)
    niu = serializers.CharField(max_length=50, required=False, allow_blank=True)

    DOCUMENT_FIELD_MAP = {
        "doc_location_plan": (
            PersonalDocument.DocumentType.LOCATION_PLAN,
            validate_document_file,
            True,
        ),
        "doc_niu": (
            PersonalDocument.DocumentType.NIU_DOCUMENT,
            validate_document_file,
            False,
        ),
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        document_errors = {}
        for field_name, (doc_type, validator, required) in self.DOCUMENT_FIELD_MAP.items():
            file = attrs.get(field_name)
            if file:
                try:
                    validator(file)
                except DjangoValidationError as e:
                    document_errors[field_name] = e.messages
            elif required:
                document_errors[field_name] = ["This document is required."]
        if document_errors:
            raise serializers.ValidationError(document_errors)
        return attrs

    @transaction.atomic
    def save(self):
        try:
            role = Role.objects.get(slug="personal")
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                "Personal role is not configured. Contact support."
            )

        user = self._create_base_user(self.validated_data, role)
        profile = PersonalProfile.objects.create(
            user=user,
            niu=self.validated_data.get("niu", ""),
        )

        for field_name, (doc_type, _, required) in self.DOCUMENT_FIELD_MAP.items():
            file = self.validated_data.get(field_name)
            if file:
                PersonalDocument.objects.create(
                    profile=profile,
                    document_type=doc_type,
                    file=file,
                    original_filename=file.name,
                )

        return user


class PersonalReapplySerializer(BaseReapplySerializer):

    doc_location_plan = serializers.FileField()
    doc_niu = serializers.FileField(required=False)
    niu = serializers.CharField(max_length=50, required=False, allow_blank=True)

    DOCUMENT_FIELD_MAP = {
        "doc_location_plan": (
            PersonalDocument.DocumentType.LOCATION_PLAN,
            validate_document_file,
            True,
        ),
        "doc_niu": (
            PersonalDocument.DocumentType.NIU_DOCUMENT,
            validate_document_file,
            False,
        ),
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        document_errors = {}
        for field_name, (doc_type, validator, required) in self.DOCUMENT_FIELD_MAP.items():
            file = attrs.get(field_name)
            if file:
                try:
                    validator(file)
                except DjangoValidationError as e:
                    document_errors[field_name] = e.messages
            elif required:
                document_errors[field_name] = ["This document is required."]
        if document_errors:
            raise serializers.ValidationError(document_errors)
        return attrs

    @transaction.atomic
    def save(self):
        from apps.audit.models import AuditLog

        user = self.validated_data["_user"]
        profile, _ = PersonalProfile.objects.get_or_create(user=user)

        profile.documents.all().delete()

        profile.niu = self.validated_data.get("niu", profile.niu)
        profile.admin_notes = ""
        profile.reviewed_by = None
        profile.reviewed_at = None
        profile.save(update_fields=["niu", "admin_notes", "reviewed_by", "reviewed_at"])

        for field_name, (doc_type, _, required) in self.DOCUMENT_FIELD_MAP.items():
            file = self.validated_data.get(field_name)
            if file:
                PersonalDocument.objects.create(
                    profile=profile,
                    document_type=doc_type,
                    file=file,
                    original_filename=file.name,
                )

        self._reset_user_to_pending(user)

        AuditLog.log(
            AuditLog.EventType.REAPPLICATION,
            user=user,
            metadata={"role": "personal"},
        )

        send_reapplication_confirmation(user)

        return user