# Shoonya Backend

Repository for Shoonya's backend.

## Pre-requisites

The project was created using [Python 3.7](https://www.python.org/downloads/). All major dependencies along with the versions are listed in the `backend/deploy/requirements.txt` file.

## Installation



# Project Name README

## Prerequisites
- Docker Engine/Docker Desktop running

## Database Setup
To set up a PostgreSQL container:
- When prompted during the script execution, enter 'Y' to include PostgreSQL installation.
- Alternatively, manually provide the following database variables in the `.env` file:
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`

## Default Components
This section includes the default setup required for the application to work. It contains Docker deployments of Django, Celery, and Redis.

### Django
- Description: Django is a high-level Python web framework.
- Configuration:
  - `SECRET_KEY`: Django secret key

### Celery
- Description: Celery is an asynchronous task queue/job queue based on distributed message passing.
- Configuration:
  - `CELERY_BROKER_URL`: Broker for Celery tasks

### Redis
- Description: Redis is an open-source, in-memory data structure store used as a database, cache, and message broker.
- Configuration: None

## Elasticsearch-Logstash-Kibana
This section contains the ELK stack for logging monitoring etc.

- Elasticsearch
  - Description: Elasticsearch is a distributed, RESTful search and analytics engine.
  - Configuration:
    - `ELASTICSEARCH_URL`: URL for Elasticsearch
    - `INDEX_NAME`: Index name

- Logstash
  - Description: Logstash is a server-side data processing pipeline that ingests data from multiple sources simultaneously, transforms it, and then sends it to a "stash" like Elasticsearch.
  - Configuration: None

- Kibana
  - Description: Kibana is an open-source data visualization dashboard for Elasticsearch.
  - Configuration: None

## Nginx-Certbot
This section contains Nginx and Certbot setup for serving HTTPS traffic.

- Nginx
  - Description: Nginx is a web server that can also be used as a reverse proxy, load balancer, mail proxy, and HTTP cache.
  - Configuration: None

- Certbot
  - Description: Certbot is a free, open-source software tool for automatically using Let's Encrypt certificates on manually-administrated websites to enable HTTPS.
  - Configuration: None

## Additional Services

### Google Application Credentials
- Description: Google Application Credentials for accessing Google APIs.
- Parameters:
  - `type`
  - `project_id`
  - `private_key_id`
  - `private_key`
  - `client_email`
  - `client_id`
  - `auth_uri`
  - `token_uri`
  - `auth_provider_x509_cert_url`
  - `client_x509_cert_url`
  - `universe_domain`

### Ask_Dhruva
- Description: Component for interacting with Dhruva ASR service.
- Parameters:
  - `ASR_DHRUVA_URL`: URL for Dhruva ASR service
  - `ASR_DHRUVA_AUTHORIZATION`: Authorization token for Dhruva ASR service

### Indic_Trans_V2
- Description: Component for interacting with Indic Trans V2 service.
- Parameters:
  - `INDIC_TRANS_V2_KEY`: API key for Indic Trans V2 service
  - `INDIC_TRANS_V2_URL`: URL for Indic Trans V2 service

### Email Service
- Description: Required for the application to work. Contains a Docker deployment of Django, Celery, and Redis.
- Parameters:
  - `EMAIL_HOST`
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `DEFAULT_FROM_EMAIL`

### Logging
- Description: Required for the application to work. Contains a Docker deployment of Django, Celery, and Redis.
- Parameters:
  - `LOGGING`
  - `LOG_LEVEL`

### MINIO
- Description: Required for the application to work. Contains a Docker deployment of Django, Celery, and Redis.
- Parameters:
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `MINIO_ENDPOINT`

## Running the Setup Script
To run the setup script:
1. Clone this repository to your local machine.
2. Navigate to the root directory of the project.
3. Run the following command: `python deploy.py`


## What the script does?
- Automatically creates a Docker network named `shoonya_backend`.
- Prompts the user to choose whether to run the application in production mode.
- Guides the user through setting up a PostgreSQL container if desired.
- Allows selection of components and sets up Docker Compose files accordingly.
- Manages environment variables in the `.env` file for each selected component.
- Deploys Docker containers for selected components.
- Provides feedback and error handling throughout the setup process.




