from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom manager for our email-based User model.
    Handles user creation for both regular users and superusers.
    """

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not extra_fields.get("first_name"):
            raise ValueError("First name is required.")
        if not extra_fields.get("last_name"):
            raise ValueError("Last name is required.")
        if not extra_fields.get("phone_number"):
            raise ValueError("Phone number is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates a standard user.
        is_active=False by default — account must be approved
        by an admin before the user can log in. This applies
        to both student and personal account types.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", False)  # always starts inactive

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, phone_number, password=None, **extra_fields):
        """
        Creates a superuser for the Django admin.
        Superusers bypass the KYC flow entirely.
        Phone number defaults to empty string for superusers
        since they are created via CLI, not the registration flow.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("first_name", "Admin")
        extra_fields.setdefault("last_name", "User")
        extra_fields.setdefault("phone_number", "")

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, phone_number, **extra_fields)
