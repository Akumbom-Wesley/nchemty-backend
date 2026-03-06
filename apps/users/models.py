from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class Role(models.Model):
    """
    Represents a user role in the system (e.g. 'student', 'personal').
    Kept as a DB model so new roles can be added without code changes.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    # Drives the auth wizard — controls what steps registration requires.
    # Structure:
    # {
    #   "requires_2fa": false,          ← commented out for now, always false
    #   "requires_documents": true,
    #   "requires_admin_approval": true
    # }
    auth_config = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    # ── Config helpers ───────────────────────────────────────────

    @property
    def requires_2fa(self):
        # Hardcoded False for now — 2FA commented out across the system
        return False

    @property
    def requires_documents(self):
        return self.auth_config.get("requires_documents", False)

    @property
    def requires_admin_approval(self):
        return self.auth_config.get("requires_admin_approval", True)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model. Email is the primary identifier.
    First name, last name, and phone are required for all account types
    as part of the KYC serializers information.
    """

    class AccountStatus(models.TextChoices):
        PENDING = "pending", "Pending Verification"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REJECTED = "rejected", "Rejected"

    # ── Core identity ────────────────────────────────────────────

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    # Phone is required at registration for all account types.
    # Stored here (not in profile) because it's serializers identity,
    # not role-specific information.
    phone_number = models.CharField(max_length=20, unique=True)

    # ── Role ─────────────────────────────────────────────────────

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    # ── Account state ────────────────────────────────────────────

    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
        db_index=True,
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone_number"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    # ── Name helpers ─────────────────────────────────────────────

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    # ── Status helpers ───────────────────────────────────────────

    @property
    def is_verified(self):
        return self.account_status == self.AccountStatus.ACTIVE and self.is_active

    @property
    def is_pending(self):
        return self.account_status == self.AccountStatus.PENDING

    # ── State transitions ────────────────────────────────────────
    # All state changes go through these methods — never set
    # is_active or account_status directly from outside the model.

    def activate(self):
        self.is_active = True
        self.account_status = self.AccountStatus.ACTIVE
        self.save(update_fields=["is_active", "account_status"])

    def suspend(self):
        self.is_active = False
        self.account_status = self.AccountStatus.SUSPENDED
        self.save(update_fields=["is_active", "account_status"])

    def reject(self):
        self.is_active = False
        self.account_status = self.AccountStatus.REJECTED
        self.save(update_fields=["is_active", "account_status"])

    # ── Role helpers ─────────────────────────────────────────────

    def get_auth_config(self):
        return self.role.auth_config if self.role else {}

    def requires_documents(self):
        return self.role.requires_documents if self.role else False