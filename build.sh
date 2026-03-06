#!/usr/bin/env bash
set -o errexit

pip install -r requirements/requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_roles
python manage.py create_superuser_if_none