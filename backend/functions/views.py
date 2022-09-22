import ast
import json

from dataset import models as dataset_models
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tasks.models import *

from .tasks import (
    sentence_text_translate_and_save_translation_pairs,
    conversation_data_machine_translation,
)
from .utils import (
    check_if_particular_organization_owner,
    check_translation_function_inputs,
    check_conversation_translation_function_inputs,
)

from users.utils import (
    INDIC_TRANS_SUPPORTED_LANGUAGES,
    LANG_TRANS_MODEL_CODES,
    TRANSLATOR_BATCH_SIZES,
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
    api_type = request.data.get("api_type", "indic-trans")

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
