from dotenv import load_dotenv
import os

load_dotenv()

address = os.getenv("FLOWER_ADDRESS")
port = int(os.getenv("FLOWER_PORT"))
broker_url = os.getenv("CELERY_BROKER_URL")
broker = os.getenv("CELERY_BROKER_URL")

# Enable basic authentication
flower_username = os.getenv("FLOWER_USERNAME")
flower_password = os.getenv("FLOWER_PASSWORD")
basic_auth = f"{flower_username}:{flower_password}"
