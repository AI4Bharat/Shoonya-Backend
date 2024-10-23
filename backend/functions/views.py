import ast
import json
import os

from azure.storage.blob import BlobServiceClient

from anudesh_backend.locks import Lock
from urllib import request

from dataset import models as dataset_models
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.utils import (
    INDIC_TRANS_SUPPORTED_LANGUAGES,
    LANG_TRANS_MODEL_CODES,
    TRANSLATOR_BATCH_SIZES,
)

from tasks.models import *
from utils.blob_functions import test_container_connection
from utils.llm_interactions import get_model_output

from .tasks import (
    populate_draft_data_json,
    schedule_mail_for_project_reports,
    schedule_mail_to_download_all_projects,
)
from .utils import (
    check_if_particular_organization_owner,
)


@api_view(["GET"])
def get_indic_trans_supported_langs_model_codes(request):
    """Function to get the supported languages and the translations supported by the indic-trans models"""

    # Return the allowed translations and model codes
    return Response(
        {
            "supported_languages": INDIC_TRANS_SUPPORTED_LANGUAGES,
            "indic_trans_model_codes": LANG_TRANS_MODEL_CODES,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def schedule_draft_data_json_population(request):
    """
    Request Body{
        "dataset_instance_id":<int>,
        "fields_list":<str>(fields separated by commas),
        "organization_id": <int>,
    }
    """

    # Check if the user is the organization owner
    result = check_if_particular_organization_owner(request)
    if result["status"] in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]:
        return Response({"error": result["error"]}, status=result["status"])

    fields_list = request.data["fields_list"]
    fields_list = fields_list.split(",")
    pk = request.data["dataset_instance_id"]

    populate_draft_data_json.delay(pk, fields_list)

    ret_dict = {"message": "draft_data_json population started"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


@api_view(["POST"])
def schedule_project_reports_email(request):
    (
        workspace_level_reports,
        organization_level_reports,
        dataset_level_reports,
        wid,
        oid,
        did,
    ) = (False, False, False, 0, 0, 0)
    if "workspace_id" in request.data:
        workspace_level_reports = True
        wid = request.data.get("workspace_id")
    elif "organization_id" in request.data:
        organization_level_reports = True
        oid = request.data.get("organization_id")
    elif "dataset_id" in request.data:
        dataset_level_reports = True
        did = request.data.get("dataset_id")
    else:
        ret_dict = {
            "message": "Please send a workspace_id or a organization_id or a dataset_id"
        }
        ret_status = status.HTTP_400_BAD_REQUEST
        return Response(ret_dict, status=ret_status)

    anno_stats, meta_stats, complete_stats = False, False, False
    if "annotation_statistics" in request.data:
        anno_stats = True
    elif "meta-info_statistics" in request.data:
        meta_stats = True
    elif "complete_statistics" in request.data:
        complete_stats = True
    else:
        ret_dict = {"message": "Please send a statistics_type"}
        ret_status = status.HTTP_400_BAD_REQUEST
        return Response(ret_dict, status=ret_status)

    try:
        user_id = request.data.get("user_id")
    except KeyError:
        return Response(
            {"message": "Please send an user id"}, status=status.HTTP_404_NOT_FOUND
        )
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    if not (
        user.is_authenticated
        and (
            user.role in [User.ORGANIZATION_OWNER, User.WORKSPACE_MANAGER, User.ADMIN]
            or user.is_superuser
        )
    ):
        final_response = {
            "message": "You do not have enough permissions to access this!"
        }
        return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

    try:
        project_type = request.data.get("project_type")
    except KeyError:
        return Response(
            {"message": "Please send the project type"},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        language = request.data.get("language")
    except KeyError:
        language = "NULL"

    # name of the task is the same as the name of the celery function + all the parameters that are passed to it
    uid = request.user.id
    task_name = (
        "schedule_mail_for_project_reports"
        + str(project_type)
        + str(anno_stats)
        + str(meta_stats)
        + str(complete_stats)
        + str(workspace_level_reports)
        + str(organization_level_reports)
        + str(dataset_level_reports)
        + str(wid)
        + str(oid)
        + str(did)
        + str(language)
    )
    celery_lock = Lock(uid, task_name)
    try:
        lock_status = celery_lock.lockStatus()
    except Exception as e:
        print(
            f"Error while retrieving the status of the lock for {task_name} : {str(e)}"
        )
        lock_status = 0  # if lock status is not received successfully, it is assumed that the lock doesn't exist

    if lock_status == 0:
        celery_lock_timeout = int(os.getenv("DEFAULT_CELERY_LOCK_TIMEOUT"))
        try:
            celery_lock.setLock(celery_lock_timeout)
        except Exception as e:
            print(f"Error while setting the lock for {task_name}: {str(e)}")

        schedule_mail_for_project_reports.delay(
            project_type,
            user_id,
            anno_stats,
            meta_stats,
            complete_stats,
            workspace_level_reports,
            organization_level_reports,
            dataset_level_reports,
            wid,
            oid,
            did,
            language,
        )

        return Response(
            {"message": "You will receive an email with the reports shortly"},
            status=status.HTTP_200_OK,
        )
    else:
        try:
            remaining_time = celery_lock.getRemainingTimeForLock()
        except Exception as e:
            print(f"Error while retrieving the lock remaining time for {task_name}")
            return Response(
                {"message": f"Your request is already being worked upon"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "message": f"Your request is already being worked upon, you can try again after {remaining_time}"
            },
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
def download_all_projects(request):
    (
        workspace_level_projects,
        dataset_level_projects,
        wid,
        did,
    ) = (False, False, 0, 0)
    if "workspace_id" in request.query_params:
        workspace_level_projects = True
        wid = request.query_params["workspace_id"]
    elif "dataset_id" in request.query_params:
        dataset_level_projects = True
        did = request.query_params["dataset_id"]
    else:
        ret_dict = {"message": "Please send a workspace_id or a dataset_id"}
        ret_status = status.HTTP_400_BAD_REQUEST
        return Response(ret_dict, status=ret_status)

    try:
        user_id = request.data.get("user_id")
    except KeyError:
        return Response(
            {"message": "Please send an user id"}, status=status.HTTP_404_NOT_FOUND
        )
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    if not (
        user.is_authenticated
        and (
            user.role in [User.ORGANIZATION_OWNER, User.WORKSPACE_MANAGER, User.ADMIN]
            or user.is_superuser
        )
    ):
        final_response = {
            "message": "You do not have enough permissions to access this!"
        }
        return Response(final_response, status=status.HTTP_401_UNAUTHORIZED)

    # Checking lock status, name parameter of the lock is the name of the celery function + all of it's parameters in string form
    task_name = (
        "schedule_mail_to_download_all_projects"
        + str(workspace_level_projects)
        + str(dataset_level_projects)
        + str(wid)
        + str(did)
    )

    celery_lock = Lock(user_id, task_name)
    try:
        lock_status = celery_lock.lockStatus()
    except Exception as e:
        print(
            f"Error while retrieving the status of the lock for {task_name} : {str(e)}"
        )
        lock_status = 0  # if lock status is not received successfully, it is assumed that the lock doesn't exist

    if lock_status == 0:
        schedule_mail_to_download_all_projects.delay(
            workspace_level_projects=workspace_level_projects,
            dataset_level_projects=dataset_level_projects,
            wid=wid,
            did=did,
            user_id=user_id,
        )

        return Response(
            {"message": "You will receive an email with the download link shortly"},
            status=status.HTTP_200_OK,
        )
        pass
    else:
        try:
            remaining_time = celery_lock.getRemainingTimeForLock()
        except Exception as e:
            print(f"Error while retrieving the lock remaining time for {task_name}")
            return Response(
                {"message": f"Your request is already being worked upon"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "message": f"Your request is already being worked upon, you can try again after {remaining_time}"
            },
            status=status.HTTP_200_OK,
        )


@permission_classes([AllowAny])
@api_view(["POST"])
def chat_log(request):
    try:
        interaction_json = request.data.get("interaction_json")
        now = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
        connection_string = os.getenv("CONNECTION_STRING_CHAT_LOG")
        container_name = os.getenv("CONTAINER_CHAT_LOG")
        if not test_container_connection(connection_string, container_name):
            return Response(
                {
                    "message": "Failed to establish the connection with the blob container"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        container_client = blob_service_client.get_container_client(container_name)
        name = f"{now} Anudesh interactions dump.log"
        blob_client = container_client.get_blob_client(name)
        if blob_client.exists():
            existing_data = blob_client.download_blob()
            existing_content = existing_data.readall().decode("utf-8")
            existing_json_data = json.loads(existing_content)
            existing_json_data += interaction_json
        else:
            existing_json_data = json.dumps(interaction_json, indent=2)
        blob_client.upload_blob(existing_json_data, overwrite=True)
        return Response(
            {"message": "Data stored successfully"},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response(
            {"message": "Failed to store data", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@permission_classes([AllowAny])
@api_view(["POST"])
def chat_output(request):
    prompt = request.data.get("message")
    history = request.data.get("history", "")
    model = request.data.get("model", "GPT3.5")
    return Response(
        {
            "message": get_model_output(
                "We will be rendering your response on a frontend. so please add spaces or indentation or nextline chars or "
                "bullet or numberings etc. suitably for code or the text. wherever required.",
                prompt,
                history,
                model,
            )
        },
        status=status.HTTP_200_OK,
    )
