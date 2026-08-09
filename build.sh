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
