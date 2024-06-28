from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from loging.serializers import TransliterationSerializer, TransliterationLogSerializer
from azure.storage.blob import BlobServiceClient
from .tasks import retrieve_logs_and_send_through_email
from users.models import User
from rest_framework.permissions import IsAuthenticated
from utils.blob_functions import test_container_connection
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.decorators import action

import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
TRANSLITERATION_CONTAINER_NAME = os.getenv("TRANSLITERATION_CONTAINER_NAME")


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
            retrieve_logs_and_send_through_email.delay(
                start_date_str, end_date_str, user.email
            )
        except Exception as e:
            return Response(
                {"message": "Failed to retrieve logs", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TransliterationLogView(APIView):
    def post(self, request):
        # Validate that the payload contains exactly three words
        if len(request.data) != 3:
            return Response(
                {"error": "Payload must contain exactly three words."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TransliterationLogSerializer(data=request.data)
        if serializer.is_valid():
            # Process the valid data here
            data = serializer.validated_data
            self.log_transliteration(data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def log_transliteration(self, data):
        try:
            current_time = datetime.datetime.now().isoformat()
            data_with_timestamp = {**data, "timestamp": current_time}

            # Azure Blob Storage setup
            blob_service_client = BlobServiceClient.from_connection_string(
                self.AZURE_STORAGE_CONNECTION_STRING
            )
            container_client = blob_service_client.get_container_client(
                self.TRANSLITERATION_CONTAINER_NAME
            )
            current_date = datetime.date.today().isoformat()
            log_file_name = f"{current_date}.log"
            blob_client = container_client.get_blob_client(log_file_name)

            if not blob_client.exists():
                blob_client.upload_blob("[]", overwrite=True)

            existing_data = blob_client.download_blob().readall().decode("utf-8")
            existing_json_data = json.loads(existing_data)
            existing_json_data.append(data_with_timestamp)

            updated_content = json.dumps(existing_json_data, indent=2)
            blob_client.upload_blob(updated_content, overwrite=True)
        except Exception as e:
            print(f"Failed to log transliteration data: {str(e)}")
