import datetime
import os
import zipfile
from celery import shared_task
from azure.storage.blob import BlobServiceClient
from utils.azure_blob_utils import test_container_connection
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

log_file_path = "logs/default.log"

blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)

container_client = blob_service_client.get_container_client(CONTAINER_NAME)


def get_first_and_last_date_of_current_month():
    today = datetime.date.today()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_current_month = today.replace(
        day=datetime.date(today.year, today.month + 1, 1).day
    )
    return first_day_of_current_month, last_day_of_current_month


def zip_log_file(log_file_path, start_date, end_date, zip_file_path):
    zip_file_name = (
        f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}.zip"
    )
    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(log_file_path, os.path.basename(zip_file_name))


@shared_task(name="rotate_logs")
def main():
    try:
        if not test_container_connection():
            print("Azure Blob Storage connection test failed. Exiting...")
            return

        if os.path.exists(log_file_path):
            start_date, end_date = get_first_and_last_date_of_current_month()

            zip_file_name = f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}.zip"

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
        else:
            print("Log file does not exist.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
