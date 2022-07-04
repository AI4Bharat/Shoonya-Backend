#!/bin/bash
cd /app/

/opt/venv/bin/python manage.py makemigrations --noinput
/opt/venv/bin/python manage.py migrate --noinput
/opt/venv/bin/python manage.py createsuperuser --noinput || true
/opt/venv/bin/python manage.py collectstatic --noinput
/opt/venv/bin/gunicorn --worker-tmp-dir /dev/shm shoonya_backend.wsgi:application \
        --bind "0.0.0.0:8000" --timeout 600 --threads 4 --access-logfile '-' --error-logfile '-'