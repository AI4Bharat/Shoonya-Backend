import ast
import json

import pandas as pd
from dataset import models as dataset_models
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from tasks.models import *

from .utils import get_batch_translations_using_indictrans_nmt_api


## Utility functions
def save_translation_pairs(
    languages, input_sentences, output_dataset_instance_id, batch_size
):
    """Function to save the translation pairs in the database.

    Args:
        languages (list): List of output languages for the translations.
        input_sentences (list(list)): List of input sentences in list format containing the - [input_sentence, input_language, context, quality_status]
        output_dataset_instance_id (int): ID of the output dataset instance.
        batch_size (int): Number of sentences to be translated in a single batch.
    """

    # Iterate through the languages
    for output_language in languages:

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
            return "No clean sentences found. Perform project export first."

        # Make a sentence list for valid sentences to be translated
        all_sentences_to_be_translated = input_sentences_df["corrected_text"].tolist()

        # Loop through all the sentences to be translated in batch format
        for i in range(0, len(all_sentences_to_be_translated), batch_size):

            batch_of_input_sentences = all_sentences_to_be_translated[
                i : i + batch_size
            ]

            # Get the translation using the Indictrans NMT API
            translations_output = get_batch_translations_using_indictrans_nmt_api(
                batch_of_input_sentences,
                input_sentences_df["input_language"].iloc[0],
                output_language,
            )

            # Check if translation output didn't return an error
            if isinstance(translations_output, Exception):
                return translations_output

            # Collect the translated sentences
            translated_sentences = [
                translation["target"] for translation in translations_output
            ]

            # Check if the translated sentences are equal to the input sentences
            if len(translated_sentences) != len(batch_of_input_sentences):
                return "The number of translated sentences does not match the number of input sentences."

            # Get the output dataset instance
            output_dataset_instance = dataset_models.DatasetInstance.objects.get(
                instance_id=output_dataset_instance_id
            )

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
    }

    Response Body
    {
        "message": <str>
        "result": <str>
        "status": DjangoStatusCode
    }
    """

    input_dataset_instance_id = request.data["input_dataset_instance_id"]
    languages = request.data["languages"]

    # Collect the sentences from Sentence Text based on dataset id
    input_sentences = list(
        dataset_models.SentenceText.objects.filter(
            instance_id=input_dataset_instance_id
        ).values_list("context")
    )

    # Create a google translator object
    # translator = GoogleTranslator()

    # Get the google translations for the given dataset instance and languages
    # for lang in languages:
    #     result = translator.batch_translate(sentences=input_sentences, input_lang=, output_lang: str, batch_size: int = 100)

    ret_dict = {"message": "SUCCESS!", "result": input_sentences}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict)


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

    input_dataset_instance_id = request.data["input_dataset_instance_id"]
    languages = request.data["languages"]

    # Convert string list to a list
    languages = ast.literal_eval(languages)

    # Check if the input dataset instance is a SentenceText dataset
    try:
        input_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=input_dataset_instance_id
        )

        # Check if it is a sentence Text
        if input_dataset_instance.dataset_type != "SentenceText":
            return Response(
                {"message": "Input dataset instance is not a SentenceText dataset"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except dataset_models.DatasetInstance.DoesNotExist:
        ret_dict = {"message": "Dataset instance does not exist!"}
        ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

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

    # Create a dataset instance for the output dataset
    output_dataset_instance_id = request.data["output_dataset_instance_id"]

    # Check if the output dataset instance exists and is a TranslationPair type
    try:
        output_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=output_dataset_instance_id
        )
        if output_dataset_instance.dataset_type != "TranslationPair":
            return Response(
                {"message": "Output dataset instance is not of type TranslationPair"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        else:

            # Call the function to save the TranslationPair dataset
            save_status = save_translation_pairs(
                languages,
                input_sentences,
                output_dataset_instance_id,
                batch_size=75,
            )

            if save_status != "Success":
                return Response(
                    {"message": save_status},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    except dataset_models.DatasetInstance.DoesNotExist:
        return Response(
            {
                "message": "Output dataset instance does not exist! Create a TranslationPair DatasetInstance"
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    ret_dict = {"message": "SUCCESS!"}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)
