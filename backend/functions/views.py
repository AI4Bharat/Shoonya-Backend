import ast
import json

import pandas as pd
from dataset import models as dataset_models
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from tasks.models import *

from .utils import (
    get_batch_translations_using_indictrans_nmt_api,
    get_batch_translations_using_google_translate,
    check_translation_function_inputs,
)


## Utility functions
def sentence_text_translate_and_save_translation_pairs(
    languages,
    input_dataset_instance_id,
    output_dataset_instance_id,
    batch_size,
    api_type="indic-trans",
):
    """Function to translate SentenceTexts and to save the TranslationPairs in the database.

    Args:
        languages (list): List of output languages for the translations.
        input_dataset_instance_id (int): ID of the input dataset instance.
        output_dataset_instance_id (int): ID of the output dataset instance.
        batch_size (int): Number of sentences to be translated in a single batch.
        api_type (str): Type of API to be used for translation. (default: indic-trans)
            Allowed - [indic-trans, google]
    """

    # Collect the sentences from Sentence Text based on dataset id
    input_sentences = list(
        dataset_models.SentenceText.objects.filter(
            instance_id=input_dataset_instance_id
        ).values_list(
            "id",
            "corrected_text",
            "language",
            "context",
            "quality_status",
            "metadata_json",
        )
    )

    # Convert the input_sentences list into a dataframe
    input_sentences_df = pd.DataFrame(
        input_sentences,
        columns=[
            "sentence_text_id",
            "corrected_text",
            "input_language",
            "context",
            "quality_status",
            "metadata",
        ],
    )

    # Keep only the clean sentences
    input_sentences_df = input_sentences_df[
        (input_sentences_df["quality_status"] == "Clean")
    ].reset_index(drop=True)

    # Check if the dataframe is empty
    if input_sentences_df.shape[0] == 0:
        return {"error": "No clean sentences found. Perform project export first."}

    # Make a sentence list for valid sentences to be translated
    all_sentences_to_be_translated = input_sentences_df["corrected_text"].tolist()

    # Get the output dataset instance
    output_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id=output_dataset_instance_id
    )

    # Iterate through the languages
    for output_language in languages:

        # Loop through all the sentences to be translated in batch format
        for i in range(0, len(all_sentences_to_be_translated), batch_size):

            batch_of_input_sentences = all_sentences_to_be_translated[
                i : i + batch_size
            ]

            # Check the API type
            if api_type == "indic-trans":

                # Get the translation using the Indictrans NMT API
                translations_output = get_batch_translations_using_indictrans_nmt_api(
                    batch_of_input_sentences,
                    input_sentences_df["input_language"].iloc[0],
                    output_language,
                )

                # Check if the translations output is a string or a list 
                if isinstance(translations_output, str):
                    return {"error": translations_output}
                else: 
                    translated_sentences = translations_output

            elif api_type == "google":

                # Get the translation using the Indictrans NMT API
                translations_output = get_batch_translations_using_google_translate(
                    sentence_list=batch_of_input_sentences,
                    target_language=output_language,
                )
                
                # Check if translation output returned a list or a string 
                if isinstance(translations_output, str):
                    return {"error": translations_output}
                else: 
                    translated_sentences = translations_output

            else:
                return {"error": "Invalid API type. Allowed - [indic-trans, google]"}

            # Check if the translated sentences are equal to the input sentences
            if len(translated_sentences) != len(batch_of_input_sentences):
                return {
                    "error": "The number of translated sentences does not match the number of input sentences."
                }

            # Iterate through the dataframe
            for index, row in input_sentences_df[i : i + batch_size].iterrows():

                # Get the values for the TranslationPair model
                sentence_text_id = row["sentence_text_id"]
                input_sentence = row["corrected_text"]
                input_language = row["input_language"]
                translated_sentence = translated_sentences[index - i]
                metadata = row["metadata"]
                context = row["context"]

                # Get the sentencetext model object by ID
                sentence_text_object = dataset_models.SentenceText.objects.get(
                    id=sentence_text_id
                )

                # Create and save a TranslationPair object
                translation_pair_obj = dataset_models.TranslationPair(
                    parent_data=sentence_text_object,
                    instance_id=output_dataset_instance,
                    input_language=input_language,
                    output_language=output_language,
                    input_text=input_sentence,
                    machine_translation=translated_sentence,
                    context=context,
                    metadata_json=metadata,
                )
                translation_pair_obj.save()

    return "Success"


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
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """

    # Get the post request data
    input_dataset_instance_id = request.data["input_dataset_instance_id"]
    languages = request.data["languages"]
    output_dataset_instance_id = request.data["output_dataset_instance_id"]

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
    save_status = sentence_text_translate_and_save_translation_pairs(
        languages,
        input_dataset_instance_id,
        output_dataset_instance_id,
        batch_size=128,
        api_type="google",
    )

    # Check if error in save_status
    if "error" in save_status:
        return Response(
            {"message": save_status["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ret_dict = {"message": "SUCCESS!"}
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
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """

    # Get the post request data
    input_dataset_instance_id = request.data["input_dataset_instance_id"]
    languages = request.data["languages"]
    output_dataset_instance_id = request.data["output_dataset_instance_id"]

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
    save_status = sentence_text_translate_and_save_translation_pairs(
        languages,
        input_dataset_instance_id,
        output_dataset_instance_id,
        batch_size=75,
        api_type="indic-trans",
    )

    # Check if error in save_status
    if "error" in save_status:
        return Response(
            {"message": save_status["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ret_dict = {"message": "SUCCESS!"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)
