#!/usr/bin/env bash
set -e

# Run tests
cd ./backend/
python manage.py migrate

echo "Starting celery worker"
exec celery -A shoonya_backend.celery worker --loglevel=info --concurrency=1