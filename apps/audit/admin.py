from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Read-only admin view for audit logs.
    No add/edit/delete — the audit log is immutable.
    """

    list_display = [
        "created_at", "severity_badge", "event_type",
        "email", "ip_address", "user_agent_short",
    ]
    list_filter = ["severity", "event_type", "created_at"]
    search_fields = ["email", "ip_address", "event_type"]
    readonly_fields = [f.name for f in AuditLog._meta.get_fields() if hasattr(f, "name")]
    ordering = ["-created_at"]

    # Disable all mutation actions
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def severity_badge(self, obj):
        from django.utils.html import format_html
        colors = {
            "info": "#28a745",
            "warning": "#ffc107",
            "critical": "#dc3545",
        }
        color = colors.get(obj.severity, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.severity.upper(),
        )
    severity_badge.short_description = "Severity"

    def user_agent_short(self, obj):
        return (obj.user_agent[:60] + "...") if len(obj.user_agent) > 60 else obj.user_agent
    user_agent_short.short_description = "User Agent"