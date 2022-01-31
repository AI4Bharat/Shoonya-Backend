# Shoonya Backend

Repository for Shoonya's backend.

## Pre-requisites

The project was created using [Python 3.10.2](https://www.python.org/downloads/). All other dependencies are listed below, and in the `requirements.txt` file.

- asgiref (3.5.0)
- Django (4.0.1)
- django-filter (21.1)
- djangorestframework (3.13.1)
- Markdown (3.3.6)
- pytz (2021.3)
- sqlparse (0.4.2)
- psycopg2 (2.9.3)
- python-dotenv (0.19.2)

## Installation

The installation and setup instructions have been tested on the following platforms:

- Ubuntu 20.04 LTS

If you are using a different operating system, you will have to look at external resources (eg. StackOverflow) to correct any errors.

We use PostgreSQL for our database, so make sure you have that installed. Instructions for that can be found [here](https://www.postgresql.org/download/).

We recommend creating a virtual environment for the project.

```bash
python3 -m venv env

# Activate the virtual environment
source env/bin/activate

# To leave the virtual environment, just use
deactivate
```

Once inside, install the project dependencies:

```bash
pip install -r requirements.txt
```
You are all done installing dependencies. Now, you need to create an environment file.

### Environment file

To set up the environment variables needed for the project, run the following lines:
```bash
cp .env.example .env
```

This creates an `.env` file at the root of the project. It is needed to make sure that the project runs correctly. Please go through the file and set the parameters according to your installation.

To create a new secret key, run the following commands (within the virtual environment):
```bash
# Open a Python shell
python manage.py shell

>> from django.core.management.utils import get_random_secret_key
>> get_random_secret_key()
```

Paste the value you get there into the `.env` file.

### Run Migrations and Get the server up!
Run the following commands:
```bash
# Check if there are any pending migrations
python manage.py makemigrations

# Run all pending migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

If there were no errors, congratulations! The project is up and running.