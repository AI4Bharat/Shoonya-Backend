import ast
import json

from dataset import models as dataset_models
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tasks.models import *
from utils.custom_bulk_create import multi_inheritance_table_bulk_insert

from .tasks import sentence_text_translate_and_save_translation_pairs
from .utils import (
    check_if_particular_organization_owner,
    check_translation_function_inputs,
    check_conversation_translation_function_inputs, 
    get_batch_translations_using_google_translate, 
    get_batch_translations_using_indictrans_nmt_api, 
)

from users.utils import INDIC_TRANS_SUPPORTED_LANGUAGES, LANG_TRANS_MODEL_CODES


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
def schedule_google_translate_job(request):
    """
    Schedules a Google Translate job for a given dataset instance

    Request Body
    {
        "input_dataset_instance_id": <int>,
        "languages": <list>
        "output_dataset_instance_id": <int>
        "organization_id": <int>
        "checks_for_particular_languages": <bool>
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

    # Call the function to save the TranslationPair dataset
    sentence_text_translate_and_save_translation_pairs.delay(
        languages=languages,
        input_dataset_instance_id=input_dataset_instance_id,
        output_dataset_instance_id=output_dataset_instance_id,
        batch_size=128,
        api_type="google",
        checks_for_particular_languages=checks_for_particular_languages,
    )

    ret_dict = {"message": "Creating translation pairs from the input dataset."}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


@api_view(["POST"])
def schedule_ai4b_translate_job(request):
    """
    Schedules a Google Translate job for a given dataset instance

    Request Body
    {
        "input_dataset_instance_id": <int>,
        "languages": <list>
        "output_dataset_instance_id": <int>
        "organization_id": <int>
        "checks_for_particular_languages" : <bool>
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

    # Call the function to save the TranslationPair dataset
    sentence_text_translate_and_save_translation_pairs.delay(
        languages=languages,
        input_dataset_instance_id=input_dataset_instance_id,
        output_dataset_instance_id=output_dataset_instance_id,
        batch_size=75,
        api_type="indic-trans",
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

def conversation_data_machine_translation(
    languages, 
    input_dataset_instance_id, 
    output_dataset_instance_id, 
    batch_size, 
    api_type, 
    checks_for_particular_languages, 
): 
    """Function to translate Conversation data item and to save the translations in another Conversation dataitem. 

    Args:
        languages (list): List of output languages for the translations.
        input_dataset_instance_id (int): ID of the input dataset instance.
        output_dataset_instance_id (int): ID of the output dataset instance.
        batch_size (int): Number of sentences to be translated in a single batch.
        api_type (str): Type of API to be used for translation. (default: indic-trans)
            Allowed - [indic-trans, google]
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.
    """ 

    # Get the output dataset instance
    output_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id=output_dataset_instance_id) 

    # Collect all the Conversation dataitems for the input DatasetInstance and convert to dataframe
    conversation_dataitems = dataset_models.Conversation.objects.filter(
        instance_id=input_dataset_instance_id
    ).values_list("id", "scenario", "prompt", "conversation_json", "language")

    conversation_dataitems_df = pd.DataFrame(conversation_dataitems, columns=["id", "scenario", "prompt", "conversation_json", "language"])

    # Iterate through the languages 
    for output_language in languages:
        
        all_translated_conversation_objects = []
        # Iterate through the conversation dataitems
        for index, row in conversation_dataitems_df.iterrows():
            print(index)

            # Get the instance of the Conversation dataitem
            conversation_dataitem = dataset_models.Conversation.objects.get(id=row["id"])

            # Get the conversation JSON and iterate through it
            conversation_json = row["conversation_json"]
            translated_conversation_json = []
            for conversation in conversation_json:
                
                # Get the sentence list, scenario and prompt 
                sentences_to_translate = dict(conversation).get("sentences", [])
                speaker_id = dict(conversation).get("speaker_id", None)
                sentence_count = len(sentences_to_translate)
                sentences_to_translate.append(row["scenario"]) 
                sentences_to_translate.append(row["prompt"])
            
                # Check the API type
                if api_type == "indic-trans":

                    # Get the translation using the Indictrans NMT API
                    translations_output = get_batch_translations_using_indictrans_nmt_api(
                        sentence_list=sentences_to_translate,
                        source_language=row["language"],
                        target_language=output_language,
                        checks_for_particular_languages=checks_for_particular_languages,
                    )

                    # Check if the translations output is a string or a list
                    if isinstance(translations_output, str):

                        # Update the task status and raise an exception
                        # self.update_state(
                        #     state="FAILURE",
                        #     meta={
                        #         "Error: {}".format(translations_output),
                        #     },
                        # )

                        return {
                            "error": translations_output,
                            "status": status.HTTP_400_BAD_REQUEST,
                        }

                        raise Exception(translations_output)

                elif api_type == "google":
                    # Get the translation using the Indictrans NMT API
                    translations_output = get_batch_translations_using_google_translate(
                        sentence_list=sentences_to_translate,
                        source_language=row["language"],
                        target_language=output_language,
                        checks_for_particular_languages=checks_for_particular_languages,
                    )
                    # Check if translation output returned a list or a string
                    if type(translations_output) != list:
                        # Update the task status and raise an exception
                        # self.update_state(
                        #     state="FAILURE",
                        #     meta={
                        #         "Google API Error",
                        #     },
                        # )

                        return {
                            "message": translations_output,
                            "status": status.HTTP_400_BAD_REQUEST,
                        }

                        raise Exception("Google API Error")

                else: 
                    # Update the task status and raise an exception
                    # self.update_state(
                    #     state="FAILURE",
                    #     meta={
                    #         "Error: Invalid API type",
                    #     },
                    # )

                    return {
                        "message": "Invalid API type",
                        "status": status.HTTP_400_BAD_REQUEST,
                    }

                    raise Exception("Invalid API type")

                # Append the translations to the translated conversation JSON
                translated_conversation_json.append({"sentences": translations_output[:sentence_count], "speaker_id": speaker_id})

            # Create the Conversation object
            conversation_object = dataset_models.Conversation(
                instance_id=output_dataset_instance,
                parent_data=conversation_dataitem,
                domain=conversation_dataitem.domain,
                topic=conversation_dataitem.topic,
                speaker_count=conversation_dataitem.speaker_count,
                speakers_json=conversation_dataitem.speakers_json,
                scenario=translations_output[-2],
                prompt=translations_output[-1],
                machine_translated_conversation_json=translated_conversation_json,
                language=output_language,
            )
            
            # Append the conversation object to the list
            all_translated_conversation_objects.append(conversation_object)
        
        # Save the Conversation objects in bulk
        multi_inheritance_table_bulk_insert(all_translated_conversation_objects)
    
    return {
        "message": "Translation completed!",
        "status": status.HTTP_200_OK,
    }

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
    output = conversation_data_machine_translation(
        languages=languages,
        input_dataset_instance_id=input_dataset_instance_id,
        output_dataset_instance_id=output_dataset_instance_id,
        batch_size=75,
        api_type=api_type,
        checks_for_particular_languages=checks_for_particular_languages,
    )

    if output["status"] in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]: 
        return Response(
            {"message": output["message"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ret_dict = {"message": "Translating Conversation Dataitems"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status) 