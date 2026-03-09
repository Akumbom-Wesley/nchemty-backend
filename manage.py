#!/usr/bin/env python
import os
import sys


def main():
    # Load .env file before reading environment variables
    # so DJANGO_ENV is available even if not set in the shell
    try:
        from decouple import config
        django_env = config("DJANGO_ENV", default="development")
    except ImportError:
        django_env = os.environ.get("DJANGO_ENV", "development")

    if django_env == "production":
        settings_module = "config.settings.production"
    else:
        settings_module = "config.settings.development"

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()