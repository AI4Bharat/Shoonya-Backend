import os
import subprocess
import sys

def setup_repository():
    # Clone the repository
    subprocess.run(["git", "clone", "https://github.com/AI4Bharat/Shoonya-Backend.git"])
    os.chdir("Shoonya-Backend")
    # Switch to the development branch
    subprocess.run(["git", "checkout", "dev"])
    subprocess.run(["git", "pull", "origin", "dev"])

def install_dependencies():
    # Create a virtual environment
    subprocess.run(["python3", "-m", "venv", "venv"])
    # Activate the virtual environment
    if sys.platform == "win32":
        activate_script = "venv\\Scripts\\activate"
    else:
        activate_script = "venv/bin/activate"
    subprocess.run(["source", activate_script])
    # Install dependencies
    subprocess.run(["pip", "install", "-r", "./backend/deploy/requirements.txt"])

def setup_env_file():
    # Copy .env.example to .env
    subprocess.run(["cp", ".env.example", "./backend/.env"])
    # Generate a new secret key
    new_secret_key = subprocess.run(["python", "-c", "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"], capture_output=True, text=True)
    new_secret_key = new_secret_key.stdout.strip()
    # Update .env with the new secret key
    with open("./backend/.env", "a") as env_file:
        env_file.write(f"\nSECRET_KEY='{new_secret_key}'\n")
    print("New secret key has been generated and updated in .env")

def run_celery_instances():
    # Start Redis server
    print("Please ensure Redis is installed and running on port 6379.")
    # Start Celery workers
    subprocess.run(["celery", "-A", "shoonya_backend.celery", "worker", "--concurrency=2", "--loglevel=info"])
    # Start Celery beat
    subprocess.run(["celery", "-A", "shoonya_backend.celery", "beat", "--loglevel=info"])

def main():
    setup_repository()
    install_dependencies()
    setup_env_file()
    run_celery_instances()

if __name__ == "__main__":
    main()
