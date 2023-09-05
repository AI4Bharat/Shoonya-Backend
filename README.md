# Shoonya Backend

Repository for Shoonya's backend.

## Pre-requisites

The project was created using [Python 3.7](https://www.python.org/downloads/). All major dependencies along with the versions are listed in the `backend/deploy/requirements.txt` file.

## Installation

The installation and setup instructions have been tested on the following platforms:

It can be done in 2 ways:-
1) using docker by running all services in containers or
2) directly running the services on local one by one (like, celery and redis).
   
If your preference is 1 over 2 please be fixed to this environment and follow the steps below it:

- Docker
- Ubuntu 20.04 OR macOs 

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
2. Follow the steps to create a Service Account from the following [Google Cloud Documentation Page](https://cloud.google.com/docs/authentication/production#create_service_account).   This will create a Service Account and generate a JSON Key for the Service Account.
3. Ensure that atleast the Project Logs Writer role (`roles/logging.logWriter`) is assigned to the created Service Account.
4. Add the `GOOGLE_APPLICATION_CREDENTIALS` variable to the `.env` file. This value of this variable should be the path to the JSON Key generated in Step 2. For example,

```bash
GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcloud-key.json"
```

### Docker Installation

`cd` back to the root folder .Once inside, build the docker containers:

```bash
docker-compose -f docker-compose-local.yml build
```

To run the containers:

```bash
docker-compose -f docker-compose-local.yml up -d
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

If your preference is 2 over 1 please be fixed to this environment and follow the steps below it:

- Ubuntu 20.04 OR macOs

You can run the following script and each and every step for setting the codebase will be done directly. Please move to a folder in your local where you would like to store the code and run the script given below there:
```bash
os=$(uname)

if [ "$os" = "Linux" ] || [ "$os" = "Darwin" ]; then

git clone https://github.com/AI4Bharat/Shoonya-Backend.git
cd Shoonya-Backend
git checkout dev
git pull origin dev
cp .env.example ./backend/.env
cd backend
python3 -m venv  venv
source venv/bin/activate

pip install -r ./deploy/requirements.txt

new_secret_key=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

env_file=".env"
if sed --version 2>&1 | grep -q 'GNU sed'; then
  sed -i "/^SECRET_KEY=/d" "$env_file"
else
  sed -i.bak "/^SECRET_KEY=/d" "$env_file"
  rm -f "$env_file.bak"
fi

echo "SECRET_KEY='$new_secret_key'" >> "$env_file"

echo "New secret key has been generated and updated in $env_file"

else
  echo "Cannot run this script on: $os"
fi
  ```

### Running background tasks 
Please install and run redis from https://redis.io/download/ on port 6379 before starting celery. 

To run background tasks for project creation, we need to run the following command in the terminal. This has also been added into the `docker-compose.yml` file.
```bash 
celery command - celery -A shoonya_backend.celery worker -l info
celery command - celery -A shoonya_backend.celery beat --loglevel=info
```

You can set use the celery to local by modifying CELERY_BROKER_URL = "redis://localhost:6379/0" in ./backend/shoonya_backend/settings.py.

We can set the concurrency and autoscale in the process as well to manage the number of worker processes in the background. Read more [here](https://stackoverflow.com/a/72366865/9757174). 

The commands will be as follows 
```bash 
celery -A shoonya_backend.celery worker --concurrency=2 --loglevel=info
celery -A shoonya_backend.celery worker --autoscale=10,3 --loglevel=info
```

### Running Linters

In case you want to raise a PR, kindly run linters as specified below. You can install black by running pip install black and use `black` 
To run `black` do:

```bash
black ./backend/
```

Happy Coding!!
