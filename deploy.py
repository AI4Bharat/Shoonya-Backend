import click
import json
import subprocess

mapping = {
    "Default Setup": {
        "file": "default.yml",
        "description": "Required for the application to work. Contains a docker deployment of Django, Celery, and Redis",
        "parameters": {
            "DB_NAME": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "postgres",
            },
            "DB_USER": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "postgres",
            },
            "DB_PASSWORD": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "postgres",
            },
            "DB_HOST": {
                "help": "If you set up a PG installation, enter the same credentials, leave these to default",
                "default": "db",
            },
            "SECRET_KEY": {
                "help": "Django secret key",
                "default": "abcd1234",
            },
            "AZURE_CONNECTION_STRING": {
                "help": "AZURE storage string",
                "default": "",
            },
            "LOGS_CONTAINER_NAME": {
                "help": "Logs container name",
                "default": "logs",
            },
        },
    },
}


@click.command()
def run_application():
    click.echo("Welcome to the application setup CLI!")
    # click.echo("Default configuration includes Django, Celery, and Redis.")
    subprocess.run(["docker", "network", "create", "shoonya_backend"], check=True)
    selected_components = []
    parameters_dict = {}

    # Ask user if they want PostgreSQL installation
    install_postgres = click.prompt(
        "Do you want to include PostgreSQL installation? (Y/N)", default="N"
    )
    if install_postgres.upper() == "Y":
        subprocess.run(
            ["docker-compose", "-f", "postgres.yml", "up", "--build", "-d"], check=True
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

        click.echo("Application setup complete!")
        subprocess.run(["docker", "ps"], check=True)
    else:
        click.echo("No components selected. Exiting.")


if __name__ == "__main__":
    run_application()
