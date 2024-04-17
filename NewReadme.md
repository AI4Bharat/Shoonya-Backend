# Shoonya Backend

Repository for Shoonya's backend.

## Pre-requisites

The project was created using [Python 3.7](https://www.python.org/downloads/). All major dependencies along with the versions are listed in the `backend/deploy/requirements.txt` file.

## Installation



<details>
  <summary><i>Wow, so fancy</i></summary>
  <b>WOW, SO BOLD</b>
</details>

# Project Name README

## Prerequisites
- **Docker Engine/Docker Desktop running** 
    You may download Docker Desktop from the table given below 
        
  | Systems| Link |
  | ---------- | ------ |
  | Windows | https://docs.docker.com/desktop/install/windows-install/ |
  | Ubuntu | https://docs.docker.com/desktop/install/ubuntu/ |
  | Unix/Mac | https://docs.docker.com/desktop/install/mac-install/|
- Python Version 3.7 or above 
- An Azure account subscription.

## Backend Setup 
The whole backend setup is divided into mainly 5 Components 
```
Backend Setup
|
|-- 1. Database Setup
|
|-- 2. Default Components
|   |-- a) Django
|   |-- b) Celery
|   |-- c) Redis
|
|-- 3. Elastic Logstash Kibana (ELK) & Flower Confirguration
|
|-- 4. Nginx-Certbot 
|
|-- 5. Additional Services
|   |-- a) Google Application Credentials
|   |-- b) Ask_Dhruva
|   |-- c) Indic_Trans_V2
|   |-- d) Email Service
|   |-- e) Logging
|   |-- f) Minio
```


<details> 
<summary style="font-size:larger; font-weight:bold"> 
  1. Database Setup
</summary>

To set up a PostgreSQL container:
- When prompted during the script execution, enter 'Y' to include PostgreSQL installation.
- Alternatively, manually provide the following database variables in the `.env` file:
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
</details>


<details> 
<summary style="font-size:larger; font-weight:bold"> 
  2. Default Components
</summary>

This section outlines the essential setup needed for the application to function properly. It encompasses Docker deployments for Django, Celery, and Redis, which form the core components of our application infrastructure.

#### a) Django
- **Description:** Django is a Python-based framework for web development, providing tools and features to build robust web applications quickly and efficiently.
- Configuration:
  - `SECRET_KEY`: Django secret key either enter manually or generate using the command 

  To create a new secret key, run the following commands (within the virtual environment):
  ```
  # Open a Python shell
  python backend/manage.py shell

  >> from django.core.management.utils import get_random_secret_key
  >> get_random_secret_key()
  ```

#### b) Celery
- **Description:** Celery is a system for asynchronous task processing based on distributed message passing, allowing computationally intensive operations to run in the background without impacting the main application's performance.
- Configuration:
  - `CELERY_BROKER_URL`: Broker for Celery tasks
  

#### c) Redis
- Description: Redis is an open-source, in-memory data structure store used as a database, cache, and message broker.
- Configuration: 
  - `REDIS_HOST`: Need to configue the port
  - `REDIS_PORT` : Need to configure the port

</details>

<details> 
<summary style="font-size:larger; font-weight:bold"> 
  3. ELK & Flower configuration
</summary>


#### a) Elasticsearch-Logstash-Kibanas
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



#### b) Flower Confirguation
- Flower is a web-based tool for     monitoring and  administrating Celery clusters. It allows you to keep track of tasks as they flow through your system, inspect the 
system's health, and perform administrative operations 
like shutting down workers. 

- Additionally, Flower would be monitoring the 
tasks defined in our tasks/ directory in 
the `backend/directory`. 

- Configuration:
    - `FLOWER_USERNAME`: Flower username
    - `FLOWER_PASSWORD`: Flower password 
    - `FLOWER_PORT`: Need to configure 

</details>

<details> 
<summary style="font-size:larger; font-weight:bold"> 
  4. Nginx-Certbot
</summary>

This section contains Nginx and Certbot setup for serving HTTPS traffic.

- Nginx
  - Description: Nginx is a web server that can also be used as a reverse proxy, load balancer, mail proxy, and HTTP cache.
  - Configuration: None

- Certbot
  - Description: Certbot is a free, open-source software tool for automatically using Let's Encrypt certificates on manually-administrated websites to enable HTTPS.
  - Configuration: None

</details>


<details> 
<summary style="font-size:larger; font-weight:bold"> 
  5 Additional Services
</summary>


These are the additional services that were not only present in certain confirguration but its actually present in whole files some of them  are global variables and some are services. 

#### a) Google Application Credentials
- **Description**: Google Application Credentials are used to authenticate and authorize applications to use Google Cloud APIs. They are a key part of Google Cloud's IAM (Identity and Access Management) system, and they allow the application to interact with Google's services securely.
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

#### b) Ask_Dhruva
- Description: Component for interacting with Dhruva ASR service.  This service is likely used in your application to convert spoken language into written text.
- Parameters:
  - `ASR_DHRUVA_URL`:  Parameter is used to tell your application where to send requests for speech recognition.
  - `ASR_DHRUVA_AUTHORIZATION`: Authorization token for Dhruva ASR service. 

#### c) Indic_Trans_V2
- Description: Component for interacting with Indic Trans V2 service.
- Parameters:
  - `INDIC_TRANS_V2_KEY`: API key for Indic Trans V2 service
  - `INDIC_TRANS_V2_URL`: URL for Indic Trans V2 service

#### d) Email Service
- **Description**: The Email Service is likely used in your application to send emails. This could be for a variety of purposes such as sending notifications, password resets, confirmation emails, sending reports etc.
- Parameters:
  - `EMAIL_HOST`
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `DEFAULT_FROM_EMAIL`

#### e) Logging
- Description:
Logging  is used to record events or actions that occur during the execution of your program. It's a crucial part of software development for debugging and monitoring purposes

- Required for the application to work. Contains a Docker deployment of Django, Celery, and Redis.
- Parameters:
  - `LOGGING` :  This is a boolean value (either 'true' or 
'false') that determines whether logging is enabled. 
  - `LOG_LEVEL` :  This sets the level of logging. 'INFO' will 
log all INFO, WARNING, ERROR, and CRITICAL level 
logs. 

#### f) MINIO
- Description: MinIO is an open-source, high-performance, AWS S3 compatible object storage system. It is typically used in applications for storing unstructured data like photos, videos, log files, backups, and container/VM images.
- Parameters:
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `MINIO_ENDPOINT`

</details>

## Running the Setup Script

To run the setup script:
1. Clone this repository to your local machine.

```bash
git clone "https://github.com/AI4Bharat/Shoonya-Backend"
```
2. Navigate to the root directory of the project.
```bash 
cd Shoonya_Backend
```
3. Run the following command: `python deploy.py` make sure the docker engine is running on your system
4. Provide the details that has been asking in the prompt and it will automatically create & run  the docker containers, volumnes and processes 




## What the script does?
- Automatically creates a Docker network named `shoonya_backend`.
- Prompts the user to choose whether to run the application in production mode.
- Guides the user through setting up a PostgreSQL container if desired.
- Allows selection of components and sets up Docker Compose files accordingly.
- Manages environment variables in the `.env` file for each selected component.
- Deploys Docker containers for selected components.
- Provides feedback and error handling throughout the setup process.




