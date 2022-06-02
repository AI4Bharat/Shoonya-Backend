# Shoonya Backend

Repository for Shoonya's backend.

## Pre-requisites

The project was created using [Python 3.7](https://www.python.org/downloads/). All major dependencies are listed below; the rest are in the `backend/deploy/requirements.txt` file.

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
- Ubuntu 20.04

If you are using a different operating system, you will have to look at external resources (eg. StackOverflow) to correct any errors.

### Create a Virtual Environment

We recommend you to create a virtual environment to install all the dependencies required for the project.

```bash
python3 -m venv <YOUR-ENVIRONMENT-NAME>
source <YOUR-ENVIRONMENT-NAME>/bin/activate # this command may be different based on your OS

# Install dependencies
pip install -r deploy/requirements-dev.txt
```

### Environment file

To set up the environment variables needed for the project, run the following lines:
```bash
cp .env.example ./backend/.env
```

This creates an `.env` file at the root of the project. It is needed to make sure that the project runs correctly. Please go through the file and set the parameters according to your installation.

To create a new secret key, run the following commands (within the virtual environment):
```bash
# Open a Python shell
python backend/manage.py shell

>> from django.core.management.utils import get_random_secret_key
>> get_random_secret_key()
```

Paste the value you get there into the `.env` file.

#### Google Cloud Logging (Optional)

If Google Cloud Logging is being used, please follow these additional steps:

1. Install the `google-cloud-logging` library using the following command:
```bash
pip install google-cloud-logging
```
2. Follow the steps to create a Service Account from the following [Google Cloud Documentation Page](https://cloud.google.com/docs/authentication/production#create_service_account). This will create a Service Account and generate a JSON Key for the Service Account.
3. Ensure that atleast the Project Logs Writer role (`roles/logging.logWriter`) is assigned to the created Service Account.
4. Add the `GOOGLE_APPLICATION_CREDENTIALS` variable to the `.env` file. This value of this variable should be the path to the JSON Key generated in Step 2. For example,

```bash
GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcloud-key.json"
```

### Docker Installation

`cd` back to the root folder .Once inside, build the docker containers:

```bash
docker-compose build
```

To run the containers:

```bash
docker-compose up -d
```

To share the database with others, just share the postgres_data and the media folder with others.

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

### Running background tasks 
To run background tasks for project creation, we need to run the following command in the terminal. This has also been added into the `docker-compose.yml` file.
```bash 
docker-compose exec web python manage.py process_tasks
``` 

### Running Linters

Installing the dev requirements file would have also installed linters. We have `flake8` and `pylint`, available.

To run `flask8` do:

```bash
flake8 ./backend/shoonya_backend/
```

To run `pylint` do:

```bash
pylint ./backend/shoonya_backend/
```
