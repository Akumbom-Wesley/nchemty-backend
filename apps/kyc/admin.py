from django.contrib import admin
from django.utils.html import format_html

from .models import (
    PersonalDocument,
    PersonalProfile,
    StudentDocument,
    StudentProfile,
)


# ── Inline document displays ──────────────────────────────────────────────────

class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 0
    readonly_fields = [
        "document_type", "original_filename",
        "file_link", "uploaded_at",
    ]
    fields = [
        "document_type", "original_filename",
        "file_link", "uploaded_at",
    ]
    can_delete = False

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">View / Download</a>',
                obj.file.url,
            )
        return "—"
    file_link.short_description = "File"


class PersonalDocumentInline(admin.TabularInline):
    model = PersonalDocument
    extra = 0
    readonly_fields = [
        "document_type", "original_filename",
        "file_link", "uploaded_at",
    ]
    fields = [
        "document_type", "original_filename",
        "file_link", "uploaded_at",
    ]
    can_delete = False

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">View / Download</a>',
                obj.file.url,
            )
        return "—"
    file_link.short_description = "File"


# ── Profile admin views ───────────────────────────────────────────────────────

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = [
        "get_full_name", "get_email", "get_phone",
        "account_status", "has_all_required_documents", "created_at",
    ]
    list_filter = ["user__account_status"]
    search_fields = [
        "user__email", "user__first_name",
        "user__last_name", "user__phone_number",
    ]
    readonly_fields = [
        "user", "created_at", "updated_at",
        "reviewed_by", "reviewed_at",
    ]
    inlines = [StudentDocumentInline]
    actions = ["approve_applications", "reject_applications"]

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = "Full Name"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"

    def get_phone(self, obj):
        return obj.user.phone_number
    get_phone.short_description = "Phone"

    def account_status(self, obj):
        return obj.user.get_account_status_display()
    account_status.short_description = "Status"

    @admin.action(description="Approve selected student applications")
    def approve_applications(self, request, queryset):
        count = 0
        for profile in queryset.select_related("user"):
            if not profile.has_all_required_documents():
                self.message_user(
                    request,
                    f"Cannot approve {profile.user.get_full_name()}: missing documents.",
                    level="warning",
                )
                continue
            profile.user.activate()
            count += 1
        if count:
            self.message_user(request, f"{count} student application(s) approved.")

    @admin.action(description="Reject selected student applications")
    def reject_applications(self, request, queryset):
        for profile in queryset.select_related("user"):
            profile.user.reject()
        self.message_user(
            request, f"{queryset.count()} student application(s) rejected."
        )


@admin.register(PersonalProfile)
class PersonalProfileAdmin(admin.ModelAdmin):
    list_display = [
        "get_full_name", "get_email", "get_phone",
        "niu", "account_status",
        "has_all_required_documents", "created_at",
    ]
    list_filter = ["user__account_status"]
    search_fields = [
        "user__email", "user__first_name",
        "user__last_name", "user__phone_number", "niu",
    ]
    readonly_fields = [
        "user", "created_at", "updated_at",
        "reviewed_by", "reviewed_at",
    ]
    inlines = [PersonalDocumentInline]
    actions = ["approve_applications", "reject_applications"]

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = "Full Name"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"

    def get_phone(self, obj):
        return obj.user.phone_number
    get_phone.short_description = "Phone"

    def account_status(self, obj):
        return obj.user.get_account_status_display()
    account_status.short_description = "Status"

    @admin.action(description="Approve selected personal account applications")
    def approve_applications(self, request, queryset):
        count = 0
        for profile in queryset.select_related("user"):
            if not profile.has_all_required_documents():
                self.message_user(
                    request,
                    f"Cannot approve {profile.user.get_full_name()}: missing documents.",
                    level="warning",
                )
                continue
            profile.user.activate()
            count += 1
        if count:
            self.message_user(
                request, f"{count} personal account application(s) approved."
            )

    @admin.action(description="Reject selected personal account applications")
    def reject_applications(self, request, queryset):
        for profile in queryset.select_related("user"):
            profile.user.reject()
        self.message_user(
            request, f"{queryset.count()} personal account application(s) rejected."
        )