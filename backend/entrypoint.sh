#!/bin/bash

APP_PORT=${PORT:-8000}
cd /app/
/opt/venv/bin/python manage.py collectstatic --noinput
/opt/venv/bin/gunicorn --worker-tmp-dir /dev/shm shoonya_backend.wsgi:application --bind "0.0.0.0:${APP_PORT}" --timeout 600