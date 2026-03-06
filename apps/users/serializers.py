from rest_framework import serializers
from .models import Role, User


class RoleSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Role.
    Exposed via /api/v1/users/roles/ so the frontend can
    dynamically build the registration role picker.
    """

    class Meta:
        model = Role
        fields = ["id", "name", "slug", "requires_documents"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Safe read representation of a user.
    Used for /me endpoints and admin-facing user detail views.
    Never exposes password, internal flags, or permission fields.
    """

    role = RoleSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    account_status_display = serializers.CharField(
        source="get_account_status_display",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "account_status",
            "account_status_display",
            "is_verified",
            "date_joined",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Allows a user to update their own safe fields.
    Role, email, and account_status can never be self-updated.
    Phone number changes would require re-verification in a
    production system — left out of self-update for now.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name"]

    def validate_first_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "First name must be at least 2 characters."
            )
        return value

    def validate_last_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "Last name must be at least 2 characters."
            )
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Handles password change for authenticated users.
    All logic lives here — the view just calls .save().
    """

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=12)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must differ from current password."}
            )
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user