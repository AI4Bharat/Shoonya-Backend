from datetime import datetime
import os
import zipfile
from azure.storage.blob import BlobServiceClient
from celery import shared_task
from azure.core.exceptions import AzureError, ResourceNotFoundError
from dotenv import load_dotenv
from loging.utils import delete_elasticsearch_documents
from utils.blob_functions import test_container_connection

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("LOGS_CONTAINER_NAME")
MAX_FILE_SIZE_LIMIT = 15000000000

log_file_dir = "/logs/logs_web/"
log_file_name = "default.log"
log_file_path = log_file_dir + log_file_name


blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)

container_client = blob_service_client.get_container_client(CONTAINER_NAME)


def get_most_recent_creation_date():
    blobs = list(container_client.list_blobs())
    if not blobs:
        return None

    most_recent_blob = max(blobs, key=lambda x: x["creation_time"])
    creation_time = most_recent_blob["creation_time"]
    most_recent_date = creation_time.date()
    return most_recent_date


def zip_log_file(zip_file_name):
    zip_file_path_on_disk = os.path.join(log_file_dir, zip_file_name)
    log_dir = os.path.dirname(log_file_path)
    zip_file_path_on_disk = os.path.join(log_dir, zip_file_name)

    with zipfile.ZipFile(zip_file_path_on_disk, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(log_file_path, os.path.basename(log_file_path))


def rotate_logs():
    flag = True
    try:
        if not test_container_connection(
            AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME
        ):
            print("Azure Blob Storage connection test failed. Exiting...")
            return

        end_date = get_most_recent_creation_date()

        if not end_date:
            end_date = datetime.today()
        start_date = datetime.today()

        zip_file_name = (
            f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}.zip"
        )

        zip_log_file(zip_file_name)

        zip_file_path_on_disk = os.path.join(log_file_dir, zip_file_name)

        blob_client = container_client.get_blob_client(zip_file_name)
        with open(zip_file_path_on_disk, "rb") as file:
            blob_client.upload_blob(file, blob_type="BlockBlob")
        os.remove(zip_file_path_on_disk)

        with open(log_file_path, "w") as log_file:
            log_file.truncate(0)

        print(
            f"Log file has been zipped as {zip_file_name}, uploaded to Azure Blob Storage, and deleted from disk."
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        flag = False
    if flag:
        delete_elasticsearch_documents()


@shared_task(name="check_size")
def check_file_size_limit():
    log_file_size = os.path.getsize(log_file_path)
    if log_file_size >= MAX_FILE_SIZE_LIMIT:
        rotate_logs()
