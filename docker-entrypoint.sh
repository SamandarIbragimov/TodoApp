#!/bin/sh
set -e

# Har ishga tushganda migratsiyalar qo'llanadi
python manage.py migrate --no-input

exec "$@"
