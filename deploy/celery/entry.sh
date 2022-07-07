#!/usr/bin/env bash
set -e

cd ./backend/

echo "Running Django Migrations ..."
python manage.py migrate --noinput

echo "Starting celery worker ..."
exec celery -A shoonya_backend.celery worker --loglevel=info --concurrency=1