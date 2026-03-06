"""
Read-only serializers for admin review views.
Used by apps/administration/serializers.py and admin.py.
"""

from rest_framework import serializers

from apps.kyc.models import (
    PersonalDocument,
    PersonalProfile,
    StudentDocument,
    StudentProfile,
)


class StudentDocumentReadSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(
        source="get_document_type_display",
        read_only=True,
    )

    class Meta:
        model = StudentDocument
        fields = [
            "id", "document_type", "document_type_display",
            "original_filename", "file", "uploaded_at",
        ]
        read_only_fields = fields


class StudentProfileReadSerializer(serializers.ModelSerializer):
    documents = StudentDocumentReadSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(
        source="user.get_full_name", read_only=True
    )
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    account_status = serializers.CharField(
        source="user.account_status", read_only=True
    )
    has_all_required_documents = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "user_email", "user_full_name", "user_phone",
            "account_status", "has_all_required_documents",
            "documents", "admin_notes", "reviewed_at", "created_at",
        ]
        read_only_fields = fields


class PersonalDocumentReadSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(
        source="get_document_type_display",
        read_only=True,
    )

    class Meta:
        model = PersonalDocument
        fields = [
            "id", "document_type", "document_type_display",
            "original_filename", "file", "uploaded_at",
        ]
        read_only_fields = fields


class PersonalProfileReadSerializer(serializers.ModelSerializer):
    documents = PersonalDocumentReadSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(
        source="user.get_full_name", read_only=True
    )
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    account_status = serializers.CharField(
        source="user.account_status", read_only=True
    )
    has_all_required_documents = serializers.BooleanField(read_only=True)

    class Meta:
        model = PersonalProfile
        fields = [
            "id", "user_email", "user_full_name", "user_phone",
            "niu", "account_status", "has_all_required_documents",
            "documents", "admin_notes", "reviewed_at", "created_at",
        ]
        read_only_fields = fields