import click
import json
import subprocess

component_mapping = {
    "Default Setup": {
        "file": "default-docker-compose.yml",
        "description": "Required for the application to work. Contains a docker deployment of Django, Celery, and Redis",
        "parameters": {
            "DB_NAME": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database name",
            },
            "DB_USER": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database user",
            },
            "DB_PASSWORD": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database password",
            },
            "DB_HOST": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "db",
                "warning": "Please provide a valid database host",
            },
            "REDIS_HOST": {
                "help": "If you are using the inbuilt redis as broker, leave these to default",
                "default": "redis",
                "warning": "Please provide a valid redis host",
            },
            "REDIS_PORT": {
                "help": "If you are using the inbuilt redis as broker, leave these to default",
                "default": "6379",
                "warning": "Please provide a valid redis port",
            },
            "CELERY_BROKER_URL": {
                "help": "Broker for celery tasks",
                "default": "redis://redis:6379/0",
                "warning": "",
            },
            "SECRET_KEY": {
                "help": "Django secret key",
                "default": "abcd1234",
                "warning": "Please provide a valid secret key",
            },
        },
    },
    "Nginx_Certbot": {
        "description": "Nginx and Certbot setup for serving HTTPS traffic",
        "parameters": {
            "DOMAINS": {
                "help": "Domains for which the certificates will be obtained",
                "default": "",
                "warning": "Please provide valid domains",
            },
            "CERTBOT_TEST_CERT": {
                "help": "Whether to use Certbot's test certificate",
                "default": "0",
                "warning": "",
            },
            "CERTBOT_RSA_KEY_SIZE": {
                "help": "Size of RSA key for the certificate",
                "default": "4096",
                "warning": "",
            },
        },
    },
    "Elasticsearch-Logstash-Kibana": {
        "file": "elk-docker-compose.yml",
        "description": "ELK stack for logging monitoring etc",
        "parameters": {
            "ELASTICSEARCH_URL": {
                "help": "url for elasticsearch",
                "default": "elasticsearch:9200",
                "warning": "Please provide a valid elasticsearch endpoint",
            },
            "INDEX_NAME": {
                "help": "",
                "default": "",
                "warning": "",
            },
        },
    },
    "Flower": {
        "file": "flower-docker-compose.yml",
        "description": "Flower for monitoring celery tasks",
        "parameters": {
            "FLOWER_ADDRESS": {
                "help": "Address for accessing Flower",
                "default": "flower",
                "warning": "Please provide a valid Flower address",
            },
            "FLOWER_PORT": {
                "help": "Port for accessing Flower",
                "default": "5555",
                "warning": "Please provide a valid port number for Flower",
            },
            "FLOWER_USERNAME": {
                "help": "Username for Flower",
                "default": "shoonya",
                "warning": "Please provide a valid username for Flower",
            },
            "FLOWER_PASSWORD": {
                "help": "Password for Flower",
                "default": "flower123",
                "warning": "Please provide a valid password for Flower",
            },
        },
    },
    "Google_Application_Credentials": {
        "description": "Google Application Credentials for accessing Google APIs",
        "parameters": {
            "type": {
                "help": "Type of service account",
                "default": "",
                "warning": "Please provide a valid type",
            },
            "project_id": {
                "help": "Project ID",
                "default": "",
                "warning": "Please provide a valid project ID",
            },
            "private_key_id": {
                "help": "Private key ID",
                "default": "",
                "warning": "Please provide a valid private key ID",
            },
            "private_key": {
                "help": "Private key",
                "default": "",
                "warning": "Please provide a valid private key",
            },
            "client_email": {
                "help": "Client email",
                "default": "",
                "warning": "Please provide a valid client email",
            },
            "client_id": {
                "help": "Client ID",
                "default": "",
                "warning": "Please provide a valid client ID",
            },
            "auth_uri": {
                "help": "Authorization URI",
                "default": "",
                "warning": "Please provide a valid authorization URI",
            },
            "token_uri": {
                "help": "Token URI",
                "default": "",
                "warning": "Please provide a valid token URI",
            },
            "auth_provider_x509_cert_url": {
                "help": "Auth provider X.509 certificate URL",
                "default": "",
                "warning": "Please provide a valid Auth provider X.509 certificate URL",
            },
            "client_x509_cert_url": {
                "help": "Client X.509 certificate URL",
                "default": "",
                "warning": "Please provide a valid Client X.509 certificate URL",
            },
            "universe_domain": {
                "help": "Universe domain",
                "default": "",
                "warning": "Please provide a valid universe domain",
            },
        },
    },
    "Ask_Dhruva": {
        "description": "Component for interacting with Dhruva ASR service",
        "parameters": {
            "ASR_DHRUVA_URL": {
                "help": "URL for Dhruva ASR service",
                "default": "",
                "warning": "Please provide a valid Dhruva ASR service URL",
            },
            "ASR_DHRUVA_AUTHORIZATION": {
                "help": "Authorization token for Dhruva ASR service",
                "default": "",
                "warning": "Please provide a valid authorization token for Dhruva ASR service",
            },
        },
    },
    "Indic_Trans_V2": {
        "description": "Component for interacting with Indic Trans V2 service",
        "parameters": {
            "INDIC_TRANS_V2_KEY": {
                "help": "API key for Indic Trans V2 service",
                "default": "",
                "warning": "Please provide a valid API key for Indic Trans V2 service",
            },
            "INDIC_TRANS_V2_URL": {
                "help": "URL for Indic Trans V2 service",
                "default": "",
                "warning": "Please provide a valid URL for Indic Trans V2 service",
            },
        },
    },
    "Email Service": {
        "description": "Required for the application to work. Contains a docker deployment of Django, Celery, and Redis",
        "parameters": {
            "EMAIL_HOST": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database name",
            },
            "SMTP_USERNAME": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database user",
            },
            "SMTP_PASSWORD": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database password",
            },
            "DEFAULT_FROM_EMAIL": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "db",
                "warning": "Please provide a valid database host",
            },
        },
    },
    "Logging": {
        "description": "Required for the application to work. Contains a docker deployment of Django, Celery, and Redis",
        "parameters": {
            "LOGGING": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database name",
            },
            "LOG_LEVEL": {
                "help": "If you set up a PG installation, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database user",
            },
        },
    },
    "MINIO": {
        "description": "Required for the application to work. Contains a docker deployment of Django, Celery, and Redis",
        "parameters": {
            "MINIO_ACCESS_KEY": {
                "help": "",
                "default": "",
                "warning": "",
            },
            "MINIO_SECRET_KEY": {
                "help": "",
                "default": "",
                "warning": "",
            },
            "MINIO_ENDPOINT": {
                "help": "",
                "default": "",
                "warning": "",
            },
        },
    },
}

environment = {
    "ENV": {
        "default": "dev",
        "help": "The environment in which the application is running. PROD : Production, DEV : Development",
    },
    "AZURE_CONNECTION_STRING": {
        "help": "AZURE storage string",
        "default": "AZURE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=dummydeveloper;AccountKey=hello/Jm+uq4gvGgd5aloGrqVxYnRs/dgPHX0G6U4XmLCtZCIeKyNNK0n3Q9oRDNE+AStMDbqXg==;EndpointSuffix=core.windows.net",
        
    },
    "LOGS_CONTAINER_NAME": {
        "help": "Logs container name",
        "default": "logs",
        
    },
}


def echo_error(error_message):
    click.secho(error_message, fg="red", bold=True)
    exit(1)


def echo_success(success_message):
    click.secho(success_message, fg="green", bold=True)


def echo_warning(warning_message):
    click.secho(warning_message, fg="yellow", bold=True)


@click.command()
def run_application():
    echo_success("Welcome to the application setup CLI!")

    try:
        subprocess.run(["docker", "network", "create", "shoonya_backend"], check=True)
        echo_success("Network created with the name shoonya_backend")
    except subprocess.CalledProcessError:
        echo_warning("Network already exists with the name shoonya. Skipping creation.")

    selected_components = []
    docker_compose_files = []
    parameters_dict = {}

    try:
        production = click.prompt(
            "Do you want to run the application in production mode? (Y/N)", default="N"
        )
        if production.upper() == "N":
            click.echo("Running in development mode")
            parameters_dict["ENVIRONMENT"] = dict({"ENV": "dev"})
        # Ask user if they want PostgreSQL installation
        install_postgres = click.prompt(
            "Do you want to include PostgreSQL installation? (Y/N)", default="N"
        )
        if install_postgres.upper() == "Y":
            subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "postgres-docker-compose.yml",
                    "up",
                    "--build",
                    "-d",
                ],
                check=True,
            )

        for key, value in mapping.items():
            choice = click.prompt(
                f"Do you want to include {key}? ({value['description']}) (Y/N)",
                default="N",
            )
            if choice.upper() == "Y":
                selected_components.append(key)
                # modify the next line such that it only appends if there is a key called "file" in the value
                if "file" in value:
                    docker_compose_files.append(value["file"])

                parameters = value.get("parameters")
                if parameters:
                    click.echo(f"Please provide values for parameters for {key}:")
                    component_params = {}
                    for param, details in parameters.items():
                        help_message = details.get("help", "")
                        default_value = details.get("default", "")
                        warning = details.get("warning", "")
                        value = click.prompt(
                            f"Enter value for {param} ({help_message})",
                            default=default_value,
                        )

                        if not value:
                            value = default_value
                        component_params[param] = value
                    parameters_dict[key] = component_params
        if parameters_dict:
            with open("backend/.env", "w") as env_file:
                for component, params in parameters_dict.items():
                    for param, value in params.items():
                        env_file.write(f"{param}={value}\n")

        if docker_compose_files:
            click.echo("Running Docker Compose...")
            for file in docker_compose_files:
                subprocess.run(
                    ["docker-compose", "-f", file, "up", "--build", "-d"], check=True
                )

            # Run docker-compose logs -f for each file
            for file in docker_compose_files:
                subprocess.run(["docker-compose", "-f", file, "logs", "-f"], check=True)

            echo_success("Application setup complete!")
            subprocess.run(["docker", "ps"], check=True)
        else:
            echo_error("No components selected. Exiting.")

    except Exception as e:
        print(f"An error occurred: {e}")
        echo_error("An error occurred. Exiting. ")
        echo_error("Stopping all running containers...")
        if docker_compose_files:
            for file in docker_compose_files:
                subprocess.run(["docker-compose", "-f", file, "down"], check=True)

            # Run docker-compose logs -f for each file
            for file in docker_compose_files:
                subprocess.run(["docker-compose", "-f", file, "logs", "-f"], check=True)

        else:
            echo_error("No components selected. Exiting.")
        exit(1)


if __name__ == "__main__":
    run_application()
