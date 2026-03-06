"""
Shared base serializers for KYC registration and reapplication.
Not imported directly by views — used only by student.py and personal.py.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.users.models import User


class BaseRegistrationSerializer(serializers.Serializer):
    """
    Shared fields and validation for all account types.
    Subclasses add role-specific document fields.
    """

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, min_length=2)
    last_name = serializers.CharField(max_length=150, min_length=2)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=12)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        value = value.lower().strip()
        existing = User.objects.filter(email=value).first()
        if existing:
            if existing.account_status == User.AccountStatus.REJECTED:
                raise serializers.ValidationError(
                    "This email belongs to a rejected account. "
                    "Please use the reapplication endpoint to reapply."
                )
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate_phone_number(self, value):
        value = value.strip()
        existing = User.objects.filter(phone_number=value).first()
        if existing:
            if existing.account_status == User.AccountStatus.REJECTED:
                raise serializers.ValidationError(
                    "This phone number belongs to a rejected account. "
                    "Please use the reapplication endpoint to reapply."
                )
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )
        digits = "".join(filter(str.isdigit, value))
        if len(digits) < 8:
            raise serializers.ValidationError(
                "Please enter a valid phone number."
            )
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def _create_base_user(self, validated_data, role):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone_number=validated_data["phone_number"],
            role=role,
        )

    def _validate_documents(self, attrs, document_field_map):
        document_errors = {}
        for field_name, (doc_type, validator, *_) in document_field_map.items():
            file = attrs.get(field_name)
            if file:
                try:
                    validator(file)
                except DjangoValidationError as e:
                    document_errors[field_name] = e.messages
        if document_errors:
            raise serializers.ValidationError(document_errors)
        return attrs


class BaseReapplySerializer(serializers.Serializer):
    """
    Shared fields and validation for all reapplication types.
    Authenticates the rejected user before accepting new documents.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        request = self.context.get("request")

        user = authenticate(
            request=request,
            username=email,
            password=attrs["password"],
        )

        if user is None:
            try:
                user = User.objects.get(email=email)
                if not user.check_password(attrs["password"]):
                    raise serializers.ValidationError("Invalid credentials.")
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "No account found with this email."
                )

        if user.account_status == User.AccountStatus.PENDING:
            raise serializers.ValidationError(
                "Your application is already under review."
            )
        if user.account_status == User.AccountStatus.ACTIVE:
            raise serializers.ValidationError(
                "Your account is already active."
            )
        if user.account_status == User.AccountStatus.SUSPENDED:
            raise serializers.ValidationError(
                "Suspended accounts cannot reapply. Please contact support."
            )
        if user.account_status != User.AccountStatus.REJECTED:
            raise serializers.ValidationError(
                "Only rejected accounts can reapply."
            )

        attrs["_user"] = user
        return attrs

    def _validate_documents(self, attrs, document_field_map):
        document_errors = {}
        for field_name, (doc_type, validator, *_) in document_field_map.items():
            file = attrs.get(field_name)
            if file:
                try:
                    validator(file)
                except DjangoValidationError as e:
                    document_errors[field_name] = e.messages
        if document_errors:
            raise serializers.ValidationError(document_errors)
        return attrs

    def _reset_user_to_pending(self, user):
        user.is_active = False
        user.account_status = User.AccountStatus.PENDING
        user.save(update_fields=["is_active", "account_status"])