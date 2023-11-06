from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from loging.serializers import TransliterationSerializer
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from .tasks import retrieve_logs, send_email_with_url
from users.models import User
from rest_framework.permissions import IsAuthenticated
from utils.blob_functions import (
    extract_account_key,
    extract_account_name,
    extract_endpoint_suffix,
    test_container_connection,
)
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()


AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
TRANSLITERATION_CONTAINER_NAME = os.getenv("TRANSLITERATION_CONTAINER_NAME")


def get_azure_credentials(connection_string):
    account_key = extract_account_key(connection_string)
    account_name = extract_account_name(connection_string)
    endpoint_suffix = extract_endpoint_suffix(connection_string)

    if not account_key or not account_name or not endpoint_suffix:
        raise Exception("Azure credentials are missing or incorrect")

    return account_key, account_name, endpoint_suffix


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


def create_empty_log_for_next_day(container_client):
    current_date = datetime.date.today()
    next_day = current_date + datetime.timedelta(days=1)
    next_day_log_file = f"{next_day.isoformat()}.log"

    blob_client = container_client.get_blob_client(next_day_log_file)

    if not blob_client.exists():
        blob_client.upload_blob("[]", overwrite=True)


class TransliterationSelectionViewSet(APIView):
    # permission_classes = (IsAuthenticated,)
    def post(self, request):
        serializer = TransliterationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                if not test_container_connection(
                    AZURE_STORAGE_CONNECTION_STRING, TRANSLITERATION_CONTAINER_NAME
                ):
                    return Response(
                        {
                            "message": "Failed to establish the connection with the blob container"
                        },
                    )
                current_date = datetime.date.today()
                log_file_name = f"{current_date.isoformat()}.log"

                blob_service_client = BlobServiceClient.from_connection_string(
                    AZURE_STORAGE_CONNECTION_STRING
                )
                container_client = blob_service_client.get_container_client(
                    TRANSLITERATION_CONTAINER_NAME
                )
                blob_client = container_client.get_blob_client(log_file_name)

                if not blob_client.exists():
                    blob_client.upload_blob("[]", overwrite=True)

                existing_data = blob_client.download_blob()
                existing_content = existing_data.readall().decode("utf-8")
                existing_json_data = json.loads(existing_content)
                existing_json_data.append(data)

                updated_content = json.dumps(existing_json_data, cls=CustomJSONEncoder)
                blob_client.upload_blob(updated_content, overwrite=True)

                create_empty_log_for_next_day(container_client)

                central_blob_client = container_client.get_blob_client("central.log")

                if not central_blob_client.exists():
                    central_blob_client.upload_blob("[]", overwrite=True)

                central_existing_data = central_blob_client.download_blob()
                central_existing_content = central_existing_data.readall().decode(
                    "utf-8"
                )
                central_existing_json_data = json.loads(central_existing_content)
                central_existing_json_data.append(data)

                central_updated_content = json.dumps(
                    central_existing_json_data, cls=CustomJSONEncoder
                )
                central_blob_client.upload_blob(central_updated_content, overwrite=True)

                return Response(
                    {"message": "Data stored in Azure Blob successfully"},
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return Response(
                    {"message": "Failed to store data in Azure Blob", "error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            if not test_container_connection(
                AZURE_STORAGE_CONNECTION_STRING, TRANSLITERATION_CONTAINER_NAME
            ):
                return Response(
                    {
                        "message": "Failed to establish the connection with the blob container"
                    },
                )
            user_id = request.query_params.get("user_id")
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")

            if user_id is None:
                return Response(
                    {"message": "user_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"message": "User with the provided user_id does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if start_date_str and end_date_str:
                task = retrieve_logs.delay(start_date_str, end_date_str)
            else:
                task = retrieve_logs.delay(None, None)

            result = task.get()
            log_content = result.get("log_content", "")
            file_name = result.get("file_name", "")
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
            result = send_email_with_url.delay(user.email, blob_url)
            task_status = result.get()

            if task_status["status"] == "success":
                return Response(
                    {"message": task_status["message"]}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": task_status["message"]},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            return Response(
                {"message": "Failed to store log content in blob", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
