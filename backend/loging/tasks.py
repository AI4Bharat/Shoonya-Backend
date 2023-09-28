from celery import shared_task
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.exceptions import ValidationError
import os

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")


@shared_task
def retrieve_logs(start_date_str, end_date_str):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)

        if not start_date_str and not end_date_str:
            central_blob_client = container_client.get_blob_client("central.log")
            if central_blob_client.exists():
                central_content = (
                    central_blob_client.download_blob().readall().decode("utf-8")
                )
                central_content = central_content.replace("][", ",")
                return {"log_content": central_content, "file_name": "central_logs.txt"}
            else:
                return {"message": "Central log data not found"}
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                return {"message": "Invalid date format. Please use 'YYYY-MM-DD'."}
            log_content = ""
            for blob in container_client.list_blobs():
                blob_client = container_client.get_blob_client(blob.name)
                content = blob_client.download_blob().readall()
                try:
                    blob_date = datetime.strptime(blob.name.split(".")[0], "%Y-%m-%d")
                    if start_date <= blob_date <= end_date:
                        log_content += content.decode("utf-8")
                except ValueError:
                    continue

            if not log_content:
                return {"message": "No log data found"}

            log_content = log_content.replace("][", ",")

            file_name = f"{start_date_str}_to_{end_date_str}_logs.txt"

            return {"log_content": log_content, "file_name": file_name}

    except Exception as e:
        return {"message": "Failed to retrieve log data", "error": str(e)}


@shared_task
def send_email_with_url(user_email, attachment_url):
    try:
        message = "Here is the link to the generated document:"
        email = EmailMessage(
            "Transliteration Logs",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
        )
        email.attach("Generated Document", attachment_url, "text/plain")
        email.send()
        return {"status": "success", "message": "Email sent successfully"}
    except ValidationError as ve:
        return {"status": "error", "message": f"Validation error: {str(ve)}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}
