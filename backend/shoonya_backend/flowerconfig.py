from dotenv import load_dotenv
import os

load_dotenv()

address = os.getenv("FLOWER_ADDRESS")
port = int(os.getenv("FLOWER_PORT"))
broker_url = os.getenv("CELERY_BROKER_URL")

# Enable basic authentication
basic_auth = ["shoonya:flower123"]
