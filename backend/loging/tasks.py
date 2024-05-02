from celery import shared_task
from datetime import datetime
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings
from utils.email_template import send_email_template_with_attachment
from utils.blob_functions import (
    extract_account_key,
    extract_account_name,
    extract_endpoint_suffix,
)
import os

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
TRANSLITERATION_CONTAINER_NAME = os.getenv("TRANSLITERATION_CONTAINER_NAME")


def get_azure_credentials(connection_string):
    account_key = extract_account_key(connection_string)
    account_name = extract_account_name(connection_string)
    endpoint_suffix = extract_endpoint_suffix(connection_string)

    if not account_key or not account_name or not endpoint_suffix:
        raise Exception("Azure credentials are missing or incorrect")

    return account_key, account_name, endpoint_suffix


@shared_task
def send_email_with_url(user_email, attachment_url):
    try:
        message = "Here is the link to the generated document:"
        compiled_msg_code = send_email_template_with_attachment(
            "Transliteration Logs",
            user_email,
            message,
        )
        msg = EmailMultiAlternatives(
            "Transliteration Logs",
            compiled_msg_code,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
        )
        msg.attach_alternative(compiled_msg_code, "text/html")
        # also attach the generated document
        msg.attach("Generated Document", attachment_url, "text/plain")
        msg.send()
        # compiled_msg.attach("Generated Document", attachment_url, "text/plain")
        # compiled_msg.send()


        # email = EmailMessage(
        #     "Transliteration Logs",
        #     message,
        #     settings.DEFAULT_FROM_EMAIL,
        #     [user_email],
        # )
        # email.attach("Generated Document", attachment_url, "text/plain")
        # email.send()
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise e


@shared_task
def retrieve_logs_and_send_through_email(start_date_str, end_date_str, user_email):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            TRANSLITERATION_CONTAINER_NAME
        )

        if not start_date_str and not end_date_str:
            central_blob_client = container_client.get_blob_client("central.log")
            if central_blob_client.exists():
                log_content = (
                    central_blob_client.download_blob().readall().decode("utf-8")
                )
                log_content = log_content.replace("][", ",")
                file_name = "central_logs.txt"
            else:
                raise Exception("Central log data not found")
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                raise Exception("Invalid date format. Please use 'YYYY-MM-DD'.")
            log_content = ""
            for blob in container_client.list_blobs():
                blob_client = container_client.get_blob_client(blob.name)
                content = blob_client.download_blob().readall()
                try:
                    blob_date = datetime.strptime(blob.name.split(".")[0], "%Y-%m-%d")
                    if start_date <= blob_date <= end_date:
                        log_content += content.decode("utf-8")
                except Exception as e:
                    print(
                        f"Failed to aggregate the logs between given dates : {str(e)}"
                    )
                    raise e

            if log_content == "":
                raise Exception("No logs found")

            log_content = log_content.replace("][", ",")

            file_name = f"{start_date_str}_to_{end_date_str}_logs.txt"

        file_name_with_prefix = f"temp_{file_name}"

        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            TRANSLITERATION_CONTAINER_NAME
        )
        blob_client = container_client.get_blob_client(file_name_with_prefix)
        blob_client.upload_blob(log_content, overwrite=True)

        expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        account_key, account_name, endpoint_suffix = get_azure_credentials(
            AZURE_STORAGE_CONNECTION_STRING
        )

        sas_token = generate_blob_sas(
            container_name=TRANSLITERATION_CONTAINER_NAME,
            blob_name=blob_client.blob_name,
            account_name=account_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )

        blob_url = f"https://{account_name}.blob.{endpoint_suffix}/{TRANSLITERATION_CONTAINER_NAME}/{blob_client.blob_name}?{sas_token}"
        send_email_with_url.delay(user_email, blob_url)

    except Exception as e:
        print(f"Failed to retrieve log data : {str(e)}")
        raise e
