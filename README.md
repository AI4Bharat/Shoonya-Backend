# Shoonya Backend

Repository for Shoonya's backend.

## Pre-requisites

The project was created using [Python 3.7](https://www.python.org/downloads/). All major dependencies are listed below; the rest are in the `backend/requirements.txt` file.

- django
- djangorestframework
- django-cors-headers
- djoser
- drf-yasg
- psycopg2
- python-dotenv


## Installation

The installation and setup instructions have been tested on the following platforms:

- Docker
- Docker-Compose

If you are using a different operating system, you will have to look at external resources (eg. StackOverflow) to correct any errors.

Once inside, build the docker containers:

```bash
docker-compose build
```

To run the containers:

```bash
docker-compose up -d
```

To share the database with others, just share the postgres_data and the media folder with others.

### Environment file

To set up the environment variables needed for the project, run the following lines:
```bash
cp .env.example ./backend/.env
```

This creates an `.env` file at the root of the project. It is needed to make sure that the project runs correctly. Please go through the file and set the parameters according to your installation.

To create a new secret key, run the following commands (within the virtual environment):
```bash
# Open a Python shell
docker-compose exec web -it python manage.py shell

>> from django.core.management.utils import get_random_secret_key
>> get_random_secret_key()
```

Paste the value you get there into the `.env` file.

### Run Migrations (required only for the first time running the project or if you make any changes in the models)
Run the following commands:
```bash
# Check if there are any pending migrations
docker-compose exec web python manage.py makemigrations

# Run all pending migrations
docker-compose exec web python manage.py migrate

# Create a superuser
docker-compose exec web python manage.py createsuperuser

```

If there were no errors, congratulations! The project is up and running.