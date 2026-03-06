# apps/users/management/commands/seed_roles.py

from django.core.management.base import BaseCommand
from apps.users.models import Role


class Command(BaseCommand):
    help = "Seeds the database with default roles"

    def handle(self, *args, **kwargs):
        roles = [
            {
                "name": "Student",
                "slug": "student",
                "auth_config": {
                    "requires_2fa": False,
                    "requires_documents": True,
                    "requires_admin_approval": True,
                },
            },
            {
                "name": "Personal",
                "slug": "personal",
                "auth_config": {
                    "requires_2fa": False,
                    "requires_documents": True,
                    "requires_admin_approval": True,
                },
            },
        ]

        for r in roles:
            obj, created = Role.objects.get_or_create(
                slug=r["slug"],
                defaults={
                    "name": r["name"],
                    "auth_config": r["auth_config"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created role: {obj.name}")
                )
            else:
                self.stdout.write(f"Already exists: {obj.name}")