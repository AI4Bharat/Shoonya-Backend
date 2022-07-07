#!/usr/bin/env bash
set -e

cd ./backend/
rm -rf /usr/src/app/logs/
mkdir /usr/src/app/logs/
touch /usr/src/app/logs/gunicorn.log
touch /usr/src/app/logs/access.log

echo "Running Django Migrations ..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Creating Django Superuser ..."
python manage.py createsuperuser --noinput || true

echo "Collecting Static Files ..."
python manage.py collectstatic --noinput

echo "Creating Cache Table ..."
python manage.py createcachetable

exec gunicorn --worker-tmp-dir /dev/shm shoonya_backend.wsgi:application \
        --bind "0.0.0.0:8000" --timeout 600 --threads 4 --access-logfile '-' --error-logfile '-'