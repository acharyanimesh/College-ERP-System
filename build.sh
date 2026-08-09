#!/usr/bin/env bash
# Render build step for the Django backend.
#
# `set -o errexit` matters more than it looks: without it a failed migration
# still produces a "successful" deploy serving an app whose schema is behind
# its code.
set -o errexit

pip install -r requirements.txt

# The React bundle is built and served by Vercel, so nothing here needs
# frontend/dist. It is listed in STATICFILES_DIRS, though, and collectstatic
# fails on a missing directory — so make sure it exists, empty is fine.
mkdir -p frontend/dist

# Django's own admin and the legacy AdminLTE assets; served by WhiteNoise.
python manage.py collectstatic --no-input

python manage.py migrate

# The first login into an empty database.
#
# Render's free plan has no shell, so `createsuperuser` cannot be run by hand
# there — without this a fresh deployment would have a working app and no way
# to get into it. Runs only when both variables are set; the `||` branch is
# what keeps `set -o errexit` from failing every later deploy, since
# createsuperuser exits non-zero once the account exists. It picks the values
# out of DJANGO_SUPERUSER_* itself.
#
# user_type defaults to 1 (HOD), so this account is both a Django superuser
# for /django-admin/ and the application's own admin in the React app.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input \
    || echo "-> admin already exists, leaving it alone"
fi
