from datetime import datetime
import os
import zipfile
import re
from azure.storage.blob import BlobServiceClient
from celery import shared_task
from azure.core.exceptions import AzureError, ResourceNotFoundError
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")
MAX_FILE_SIZE_LIMIT = 10000000000

log_file_path = "logs/default.log"

blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)

container_client = blob_service_client.get_container_client(CONTAINER_NAME)


# function to check the connection by adding and deleting the blob in the container
def test_container_connection(connection_string, container_name):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        container_client = blob_service_client.get_container_client(container_name)

        name = "connection_test"
        text_to_upload = "This is a sample text to check the connection"

        container_client.upload_blob(name, text_to_upload, overwrite=True)
        container_client.delete_blob(name)

        return True
    except ResourceNotFoundError:
        print("The specified resource does not exist.")
        return False
    except AzureError as error:
        print(f"Azure Error: {error}")
        return False
    except Exception as error:
        print(f"An error occurred: {error}")
        return False


def get_most_recent_creation_date():
    blobs = list(container_client.list_blobs())

    if not blobs:
        return None

    most_recent_blob = max(blobs, key=lambda x: x["creation_time"])
    creation_time = most_recent_blob["creation_time"]

    # Extract the date part from the datetime object
    most_recent_date = creation_time.date()

    return most_recent_date


def zip_log_file(log_file_path, start_date, end_date, zip_file_path):
    zip_file_name = (
        f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}.zip"
    )
    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(log_file_path, os.path.basename(zip_file_name))


def rotate_logs():
    log_file_size = os.path.getsize(log_file_path)
    if log_file_size < 2000:
        return
    try:
        if not test_container_connection(
            AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME
        ):
            print("Azure Blob Storage connection test failed. Exiting...")
            return

        end_date = get_most_recent_creation_date()
        #decide what should be the date if there is nothing in the blob
        if not end_date:
            end_date = datetime.today()
        start_date = datetime.today()

        zip_file_name = (
            f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}.zip"
        )

        # path to store in the disk
        zip_file_path_on_disk = f"{zip_file_name}"
        zip_log_file(log_file_path, start_date, end_date, zip_file_path_on_disk)

        blob_client = container_client.get_blob_client(zip_file_name)
        with open(zip_file_path_on_disk, "rb") as file:
            blob_client.upload_blob(file, blob_type="BlockBlob")

        # os.remove(zip_file_path_on_disk)

        with open(log_file_path, "w") as log_file:
            log_file.truncate(0)

        print(
            f"Log file has been zipped as {zip_file_name}, uploaded to Azure Blob Storage, and deleted from disk."
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")


@shared_task(name="check_size")
def check_file_size_limit():
    log_file_size = os.path.getsize(log_file_path)
    if log_file_size >= MAX_FILE_SIZE_LIMIT:
        rotate_logs()

