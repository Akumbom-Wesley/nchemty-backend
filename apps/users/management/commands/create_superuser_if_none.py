import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a superuser if none exists — safe to run on every deploy"

    def handle(self, *args, **kwargs):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Superuser already exists — skipping.")
            return

        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        first_name = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "Admin")
        last_name = os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "User")

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD "
                    "not set — skipping superuser creation."
                )
            )
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Superuser created: {email}")
        )