#!/usr/bin/env bash
# One-shot setup for a clean machine:  bash scripts/bootstrap.sh
set -euo pipefail
python -m pip install -r requirements/dev.txt
python manage.py migrate --noinput                 # migrations are committed in every app
python manage.py check
python manage.py makemigrations --check --dry-run  # verification only; must print "No changes detected"
python manage.py seed_real_media
python manage.py test
echo "OK. Create the single manager account with:  python manage.py createsuperuser"
