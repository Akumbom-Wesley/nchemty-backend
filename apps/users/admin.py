from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    readonly_fields = ["created_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = [
        "email", "first_name", "last_name",
        "phone_number", "role", "account_status",
        "is_active", "date_joined",
    ]
    list_filter = ["account_status", "is_active", "role"]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    readonly_fields = ["date_joined", "last_login"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number")}),
        (_("Role & Status"), {"fields": ("role", "account_status")}),
        (_("Permissions"), {
            "fields": (
                "is_active", "is_staff", "is_superuser",
                "groups", "user_permissions",
            )
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "first_name", "last_name",
                "phone_number", "role",
                "password1", "password2",
            ),
        }),
    )

    actions = ["activate_users", "suspend_users"]

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        for user in queryset:
            user.activate()
        self.message_user(request, f"{queryset.count()} user(s) activated.")

    @admin.action(description="Suspend selected users")
    def suspend_users(self, request, queryset):
        for user in queryset:
            user.suspend()
        self.message_user(request, f"{queryset.count()} user(s) suspended.")