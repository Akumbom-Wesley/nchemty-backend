from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit Logs"

    def ready(self):
        """
        Called once Django has fully loaded all apps and models.
        This is the correct place to register signal handlers —
        not at module level, which risks running before models exist.
        """
        from .signals import register_signals
        register_signals()