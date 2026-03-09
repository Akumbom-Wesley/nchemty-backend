import os
from django.core.wsgi import get_wsgi_application

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

application = get_wsgi_application()