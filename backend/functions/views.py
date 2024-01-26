import ast
import json
from urllib import request

from dataset import models as dataset_models
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from users.utils import (
    INDIC_TRANS_SUPPORTED_LANGUAGES,
    LANG_TRANS_MODEL_CODES,
    TRANSLATOR_BATCH_SIZES,
)

from tasks.models import *

from .tasks import (
    conversation_data_machine_translation,
    sentence_text_translate_and_save_translation_pairs,
    populate_draft_data_json,
    generate_ocr_prediction_json,
    generate_asr_prediction_json,
    schedule_mail_for_project_reports,
    schedule_mail_to_download_all_projects,
)
from .utils import (
    check_conversation_translation_function_inputs,
    check_if_particular_organization_owner,
    check_translation_function_inputs,
)


@api_view(["POST"])
def copy_from_block_text_to_sentence_text(request):
    """
    Copies each sentence from a block of text to sentence text daatset
    """
    export_dataset_instance_id = request.data["export_dataset_instance_id"]
    project_id = request.data["project_id"]
    project = Project.objects.get(pk=project_id)

    # if project.is_archived == False:
    #     ret_dict = {"message": "Project is not archived!"}
    #     ret_status = status.HTTP_403_FORBIDDEN
    #     return Response(ret_dict, status=ret_status)
    # if "copy_from_block_text_to_sentence_text" in project.metadata_json:
    #     ret_dict = {"message": "Function already applied on this project!"}
    #     ret_status = status.HTTP_403_FORBIDDEN
    #     return Response(ret_dict, status=ret_status)

    export_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id__exact=export_dataset_instance_id
    )
    # dataset_model = dataset_models.BlockText
    # input_instances = project.dataset_id
    tasks = Task.objects.filter(project_id__exact=project)
    all_sentence_texts = []
    for task in tasks:
        # TODO: Create child object from parent to optimize query
        if task.metadata_json is None:
            task.metadata_json = {}
        if task.output_data is not None:
            if "copy_from_block_text_to_sentence_text" in task.metadata_json:
                continue
            block_text = dataset_models.BlockText.objects.get(id=task.output_data.id)
            # block_text = task.output_data
            # block_text.__class__ = dataset_models.BlockText
            # block_text = dataset_models.BlockText()
            # block_text = task.output_data
            raw_text = block_text.splitted_text
            sentences = raw_text.split("\n")
            for sentence in sentences:
                sentence_text = dataset_models.SentenceText(
                    parent_data=block_text,
                    language=block_text.language,
                    text=sentence,
                    domain=block_text.domain,
                    instance_id=export_dataset_instance,
                )
                all_sentence_texts.append(sentence_text)
            task.metadata_json["copy_from_block_text_to_sentence_text"] = True
            task.task_status = FREEZED
            task.save()

    # TODO: implement bulk create if possible (only if non-hacky)
    for sentence_text in all_sentence_texts:
        sentence_text.save()
    # dataset_models.SentenceText.objects.bulk_create(all_sentence_texts)

    project.save()
    ret_dict = {"message": "SUCCESS!"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


@api_view(["POST"])
def copy_from_ocr_document_to_block_text(request):
    """
    Copies data annotated from OCR Document to Block text Dataset
    """
    export_dataset_instance_id = request.data["export_dataset_instance_id"]
    project_id = request.data["project_id"]
    project = Project.objects.get(pk=project_id)

    # if project.is_archived == False:
    #     ret_dict = {"message": "Project is not archived!"}
    #     ret_status = status.HTTP_403_FORBIDDEN
    #     return Response(ret_dict, status=ret_status)
    # if "copy_from_ocr_document_to_block_text" in project.metadata_json:
    #     ret_dict = {"message": "Function already applied on this project!"}
    #     ret_status = status.HTTP_403_FORBIDDEN
    #     return Response(ret_dict, status=ret_status)

    export_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id__exact=export_dataset_instance_id
    )
    # dataset_model = dataset_models.BlockText
    # input_instances = project.dataset_id
    tasks = Task.objects.filter(project_id__exact=project)
    all_block_texts = []
    for task in tasks:
        # TODO: Create child object from parent to optimize query
        if task.metadata_json is None:
            task.metadata_json = {}
        if task.output_data is not None:
            if "copy_from_ocr_document_to_block_text" in task.metadata_json:
                continue
            ocr_document = dataset_models.OCRDocument.objects.get(
                id=task.output_data.id
            )
            # block_text = task.output_data
            # block_text.__class__ = dataset_models.BlockText
            # block_text = dataset_models.BlockText()
            # block_text = task.output_data
            transcriptions = ocr_document.annotation_transcripts
            transcriptions = json.loads(transcriptions)

            labels = ocr_document.annotation_labels
            labels = json.loads(labels)

            body_transcriptions = []
            for i, label in enumerate(labels):
                if label["labels"][0] == "Body":
                    body_transcriptions.append(transcriptions[i])

            text = " ".join(body_transcriptions)
            # TODO: check if domain can be same as OCR domain
            block_text = dataset_models.BlockText(
                parent_data=ocr_document,
                language=ocr_document.language,
                text=text,
                domain=ocr_document.ocr_domain,
                instance_id=export_dataset_instance,
            )
            all_block_texts.append(block_text)
            task.metadata_json["copy_from_ocr_document_to_block_text"] = True
            task.task_status = FREEZED
            task.save()

    # TODO: implement bulk create if possible (only if non-hacky)
    for block_text in all_block_texts:
        block_text.save()
    # dataset_models.SentenceText.objects.bulk_create(all_sentence_texts)

    # project.metadata_json["copy_from_ocr_document_to_block_text"]=True
    # project.save()
    ret_dict = {"message": "SUCCESS!"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "input_dataset_instance_id",
            openapi.IN_QUERY,
            description=("Input Dataset Instance ID"),
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "languages",
            openapi.IN_QUERY,
            description=("List of output languages"),
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING),
            required=True,
        ),
        openapi.Parameter(
            "output_dataset_instance_id",
            openapi.IN_QUERY,
            description=("Output Dataset Instance ID"),
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "organization_id",
            openapi.IN_QUERY,
            description=("Organization ID"),
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "checks_for_particular_languages",
            openapi.IN_QUERY,
            description=("Boolean to run checks for particular languages"),
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
        openapi.Parameter(
            "api_type",
            openapi.IN_QUERY,
            description=("Type of API to use for translation"),
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            "automate_missing_data_items",
            openapi.IN_QUERY,
            description=("Boolean to translate only missing data items"),
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
    ],
    responses={200: "Starting the process of creating a machine translations."},
)
@api_view(["POST"])
def schedule_sentence_text_translate_job(request):
    """
    Schedules a job for to convert SentenceText inputs to TranslationPair outputs using a particular API

    Request Body
    {
        "input_dataset_instance_id": <int>,
        "languages": <list>
        "output_dataset_instance_id": <int>
        "organization_id": <int>
        "checks_for_particular_languages" : <bool>
        "api_type": <str>
        "automate_missing_data_items": <bool>
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """

    # Check if the user is the organization owner
    result = check_if_particular_organization_owner(request)
    if result["status"] in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]:
        return Response({"error": result["error"]}, status=result["status"])

    # Get the post request data
    try:
        input_dataset_instance_id = request.data["input_dataset_instance_id"]
        languages = request.data["languages"]
        output_dataset_instance_id = request.data["output_dataset_instance_id"]
    except KeyError:
        return Response(
            {"error": "Missing required fields in request body"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    checks_for_particular_languages = request.data.get(
        "checks_for_particular_languages", "false"
    )
    api_type = request.data.get("api_type", "indic-trans-v2")
    automate_missing_data_items = request.data.get(
        "automate_missing_data_items", "true"
    )

    # Convert checks for languages into boolean
    checks_for_particular_languages = checks_for_particular_languages.lower() == "true"

    # Convert automate_missing_data_items into boolean
    automate_missing_data_items = automate_missing_data_items.lower() == "true"

    # Convert string list to a list
    languages = ast.literal_eval(languages)

    # Perform checks on the input and output dataset instances
    dataset_instance_check_status = check_translation_function_inputs(
        input_dataset_instance_id, output_dataset_instance_id
    )

    if dataset_instance_check_status["status"] in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]:
        return Response(
            {"message": dataset_instance_check_status["message"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Set the batch-size based on api_type
    batch_size = TRANSLATOR_BATCH_SIZES.get(api_type, 75)

    # Call the function to save the TranslationPair dataset
    sentence_text_translate_and_save_translation_pairs.delay(
        languages=languages,
        input_dataset_instance_id=input_dataset_instance_id,
        output_dataset_instance_id=output_dataset_instance_id,
        batch_size=batch_size,
        api_type=api_type,
        checks_for_particular_languages=checks_for_particular_languages,
        automate_missing_data_items=automate_missing_data_items,
    )

    ret_dict = {"message": "Creating translation pairs from the input dataset."}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


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


@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "input_dataset_instance_id",
            openapi.IN_QUERY,
            description=("Input Dataset Instance ID"),
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "languages",
            openapi.IN_QUERY,
            description=("List of output languages"),
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING),
            required=True,
        ),
        openapi.Parameter(
            "output_dataset_instance_id",
            openapi.IN_QUERY,
            description=("Output Dataset Instance ID"),
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "organization_id",
            openapi.IN_QUERY,
            description=("Organization ID"),
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "checks_for_particular_languages",
            openapi.IN_QUERY,
            description=("Boolean to run checks for particular languages"),
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
        openapi.Parameter(
            "api_type",
            openapi.IN_QUERY,
            description=("Type of API to use for translation"),
            type=openapi.TYPE_STRING,
            required=False,
        ),
    ],
    responses={
        200: "Starting the process of creating a machine translations for conversation dataset."
    },
)
@api_view(["POST"])
def schedule_conversation_translation_job(request):
    """
    Schedules a Google Translate job for a given dataset instance

    Request Body
    {
        "input_dataset_instance_id": <int>,
        "languages": <list>
        "output_dataset_instance_id": <int>
        "organization_id": <int>
        "checks_for_particular_languages" : <bool>
        "api_type": <str>
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """

    # Check if the user is the organization owner
    result = check_if_particular_organization_owner(request)
    if result["status"] in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]:
        return Response({"error": result["error"]}, status=result["status"])

    # Get the post request data
    input_dataset_instance_id = request.data["input_dataset_instance_id"]
    languages = request.data["languages"]
    output_dataset_instance_id = request.data["output_dataset_instance_id"]
    checks_for_particular_languages = request.data["checks_for_particular_languages"]
    api_type = request.data["api_type"]

    # Convert string list to a list
    languages = ast.literal_eval(languages)

    # Set the batch size based on the api_type
    batch_size = TRANSLATOR_BATCH_SIZES.get(api_type, 75)

    # Perform checks on the input and output dataset instances
    dataset_instance_check_status = check_conversation_translation_function_inputs(
        input_dataset_instance_id, output_dataset_instance_id
    )

    if dataset_instance_check_status["status"] in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]:
        return Response(
            {"message": dataset_instance_check_status["message"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Call the function to save the TranslationPair dataset
    conversation_data_machine_translation.delay(
        languages=languages,
        input_dataset_instance_id=input_dataset_instance_id,
        output_dataset_instance_id=output_dataset_instance_id,
        batch_size=batch_size,
        api_type=api_type,
        checks_for_particular_languages=checks_for_particular_languages,
    )
    ret_dict = {"message": "Translating Conversation Dataitems"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "dataset_instance_id",
            openapi.IN_QUERY,
            description="Dataset Instance ID",
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "organization_id",
            openapi.IN_QUERY,
            description="Organization ID",
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            "api_type",
            openapi.IN_QUERY,
            description="Type of API to use for translation",
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            "automate_missing_data_items",
            openapi.IN_QUERY,
            description="Boolean to translate only missing data items",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
    ],
    responses={
        200: "Starting the process of populating ocr_prediction_json for OCR dataset."
    },
)
@api_view(["POST"])
def schedule_ocr_prediction_json_population(request):
    """
    Schedules a OCR prediction population job for a given dataset instance and API type.

    Request Body
    {
        "dataset_instance_id": <int>,
        "organization_id": <int>,
        "api_type": <str>,
        "automate_missing_data_items": <bool>
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """
    # Check if the user is the organization owner
    result = check_if_particular_organization_owner(request)
    if result["status"] in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]:
        return Response({"error": result["error"]}, status=result["status"])

    # Fetching request data
    try:
        dataset_instance_id = request.data["dataset_instance_id"]
    except KeyError:
        return Response(
            {"error": "Please send a dataset_instance_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        api_type = request.data["api_type"]
    except KeyError:
        api_type = "google"
    try:
        automate_missing_data_items = request.data["automate_missing_data_items"]
    except KeyError:
        automate_missing_data_items = True

    # Calling a function asynchronously to create ocr predictions.
    generate_ocr_prediction_json.delay(
        dataset_instance_id=dataset_instance_id,
        api_type=api_type,
        automate_missing_data_items=automate_missing_data_items,
    )

    # Returning response
    ret_dict = {"message": "Generating OCR Predictions"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


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
def schedule_asr_prediction_json_population(request):
    """
    Schedules a ASR prediction population job for a given dataset instance and API type.

    Request Body
    {
        "dataset_instance_id": <int>,
        "organization_id": <int>,
        "api_type": <str>,
        "automate_missing_data_items": <bool>
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """
    # Check if the user is the organization owner
    result = check_if_particular_organization_owner(request)
    if result["status"] in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]:
        return Response({"error": result["error"]}, status=result["status"])

    # Fetching request data
    try:
        dataset_instance_id = request.data["dataset_instance_id"]
    except KeyError:
        return Response(
            {"error": "Please send a dataset_instance_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        api_type = request.data["api_type"]
    except KeyError:
        api_type = "dhruva_asr"
    try:
        automate_missing_data_items = request.data["automate_missing_data_items"]
    except KeyError:
        automate_missing_data_items = True

    # Calling a function asynchronously to create ocr predictions.
    generate_asr_prediction_json.delay(  # add delay
        dataset_instance_id=dataset_instance_id,
        api_type=api_type,
        automate_missing_data_items=automate_missing_data_items,
    )

    # Returning response
    ret_dict = {"message": "Generating ASR Predictions"}
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

    schedule_mail_to_download_all_projects.delay(
        workspace_level_projects, dataset_level_projects, wid, did, user_id
    )

    return Response(
        {"message": "You will receive an email with the download link shortly"},
        status=status.HTTP_200_OK,
    )
    pass
