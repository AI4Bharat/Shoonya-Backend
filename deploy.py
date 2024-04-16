import click
import json
import subprocess
 
mapping = {
    "Default Setup": {
        "file": "default-docker-compose.yml",
        "description": "Required for the application to work. Contains a docker deployment of Django, Celery, and Redis",
        "parameters": {
            "DB_NAME": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database name",
            },
            "DB_USER": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database user",
            },
            "DB_PASSWORD": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "postgres",
                "warning": "Please provide a valid database password",
            },
            "DB_HOST": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "db",
                "warning": "Please provide a valid database host",
            },
            "SECRET_KEY": {
                "help": "Django secret key",
                "default": "abcd1234",
                "warning": "Please provide a valid secret key",
            },
            "AZURE_CONNECTION_STRING": {
                "help": "AZURE storage string",
                "default": "AZURE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=dummydeveloper;AccountKey=hello/Jm+uq4gvGgd5aloGrqVxYnRs/dgPHX0G6U4XmLCtZCIeKyNNK0n3Q9oRDNE+AStMDbqXg==;EndpointSuffix=core.windows.net",
                "warning": "Please provide a valid Azure connection string",
            },
            "LOGS_CONTAINER_NAME": {
                "help": "Logs container name",
                "default": "logs",
                "warning": "Please provide a valid logs container name",
            },
        },
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
    parameters_dict = {}

    try : 
        # Ask user if they want PostgreSQL installation
        install_postgres = click.prompt(
            "Do you want to include PostgreSQL installation? (Y/N)", default="N"
        )
        if install_postgres.upper() == "Y":
            subprocess.run(
                ["docker-compose", "-f", "postgres-docker-compose.yml", "up", "--build", "-d"], check=True
            )

        production = click.prompt(
            "Do you want to run the application in production mode? (Y/N)", default="N"
        )
        if production.upper() == "N":
            click.echo("Running in production mode")
            parameters_dict["ENVIRONMENT"] = dict({
                "ENV" : "dev"
            })
        for key, value in mapping.items():
            choice = click.prompt(
                f"Do you want to include {key}? ({value['description']}) (Y/N)", default="N"
            )
            if choice.upper() == "Y":
                selected_components.append(key)
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

        docker_compose_files = [
            mapping[component]["file"] for component in selected_components
        ]
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
                subprocess.run(
                    ["docker-compose", "-f", file, "down"], check=True
                )

            # Run docker-compose logs -f for each file
            for file in docker_compose_files:
                subprocess.run(["docker-compose", "-f", file, "logs", "-f"], check=True)

        else:
            echo_error("No components selected. Exiting.")
        exit(1)

if __name__ == "__main__":
    run_application()
