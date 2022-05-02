#!/bin/sh

python manage.py makemigrations users
python manage.py makemigrations organizations
python manage.py makemigrations workspaces
python manage.py migrate
python manage.py collectstatic --no-input --clear

exec "$@"