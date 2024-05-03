import os
import subprocess
import sys
import time
import shutil
import string
import random
def generate_secret_key(length=50):
    """
    Generate a random Django secret key.
    """
    characters = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return ''.join(random.choice(characters) for _ in range(length))

def install_dependencies():
    # Create a virtual environment
    subprocess.run(["python3", "-m", "venv", "venv"])
    # Activate the virtual environment
    if sys.platform == "win32":
        activate_script = os.path.join("venv", "Scripts", "activate.bat")
    else:
        activate_script = os.path.join("venv", "bin", "activate")
    subprocess.run([activate_script])

    # Install dependencies
    subprocess.run(["pip", "install", "-r", "./backend/deploy/requirements.txt"])


def setup_env_file():
    # Copy .env.example to .env
    shutil.copy(".env.example", "./backend/.env")
   

    # Generate a new secret key
    new_secret_key = generate_secret_key()
    # Update .env with the new secret key
    with open("./backend/.env", "a") as env_file:
        env_file.write(f"\nSECRET_KEY='{new_secret_key}'\n")
    print("New secret key has been generated and updated in .env")


def run_celery_instances():

    # Activate the virtual environment
    if sys.platform == "win32":
        activate_script = os.path.join("venv", "Scripts", "activate.bat")
    else:
        activate_script = os.path.join("venv", "bin", "activate")
    subprocess.run([activate_script])


    
    os.chdir("backend")
    
    # Start Celery workers
    celery_worker_process = subprocess.Popen(
        [
            "celery",
            "-A",
            "shoonya_backend.celery",
            "worker",
            "--concurrency=2",
            "--loglevel=info",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Start Celery beat
    celery_beat_process = subprocess.Popen(
        ["celery", "-A", "shoonya_backend.celery", "beat", "--loglevel=info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Capture and print the output
    worker_output, worker_errors = celery_worker_process.communicate()
    beat_output, beat_errors = celery_beat_process.communicate()

    print("Celery Worker Output:")
    print(worker_output.decode("utf-8"))
    print("Celery Worker Errors:")
    print(worker_errors.decode("utf-8"))

    print("Celery Beat Output:")
    print(beat_output.decode("utf-8"))
    print("Celery Beat Errors:")
    print(beat_errors.decode("utf-8"))


def start_django_server():
    # Activate the virtual environment
    if sys.platform == "win32":
        activate_script = os.path.join("venv", "Scripts", "activate.bat")
    else:
        activate_script = os.path.join("venv", "bin", "activate")
    subprocess.run([activate_script])

    # Start Django server
    print("Starting Django server...")
    subprocess.Popen(["python", "./backend/manage.py", "runserver"])


def main():
    install_dependencies()
    setup_env_file()
    run_celery_instances()
    start_django_server()


if __name__ == "__main__":
    main()
