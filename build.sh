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

# The login into an empty — or confused — database.
#
# Render's free plan has no shell, so nothing can be run by hand there. This
# replaces `createsuperuser`, which could only ever create and refused to run
# twice, and which left the account needing an emailed verification link that
# an unconfigured deployment sends to its own logs.
#
# bootstrap_admin makes the database match DJANGO_SUPERUSER_EMAIL/PASSWORD:
# right role, verified, active, password reset to the variable. Safe and
# meaningful to run on every deploy, and it needs no `||` guard because doing
# nothing is a success when the variables are unset.
python manage.py bootstrap_admin
