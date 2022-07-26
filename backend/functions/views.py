import json
import requests
import uuid

from dataset import models as dataset_models
from dataset.serializers import SentenceTextSerializer
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from tasks.models import *

# from .utils import GoogleTranslator

## Utility functions
def get_translation_using_cdac_model(input_sentence, source_language, target_language):
    """Function to get the translation for the input sentences using the CDAC model.

    Args:
        input_sentence (str): Sentence to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Final language of the sentence.

    Returns:
        str: Translated sentence.
    """

    headers = {
        # Already added when you pass json= but not when you pass data=
        # 'Content-Type': 'application/json',
    }

    json_data = {
        "input": [
            {
                "source": input_sentence,
            },
        ],
        "config": {
            "modelId": 103,
            "language": {
                "sourceLanguage": source_language,
                "targetLanguage": target_language,
            },
        },
    }

    response = requests.post(
        "https://cdac.ulcacontrib.org/aai4b-nmt-inference/v0/translate",
        headers=headers,
        json=json_data,
    )

    return response.json()["output"][0]["target"]


def save_translation_pairs(
    languages, input_sentences, output_dataset_instance_id, input_dataset_instance_id
):
    """Function to save the translation pairs in the database.

    Args:
        languages (list): List of output languages for the translations.
        input_sentences (list(list)): List of input sentences in list format containing the - [input_sentence, input_language, context, quality_status]
        output_dataset_instance_id (int): ID of the output dataset instance.
        input_dataset_instance_id (int): ID of the input dataset instance.
    """

    # Iterate through the languages
    for output_language in languages:

        # Save all the translation outputs in the TranslationPair object
        for input_sentence, language, context, quality_status in input_sentences:

            # Only perform the saving if quality status is clean
            if quality_status == "Clean":

                # Get the translations
                translated_sentence = get_translation_using_cdac_model(
                    input_sentence=input_sentence,
                    source_language=language,
                    target_language=output_language,
                )

                # Get the output dataset instance
                output_dataset_instance = dataset_models.DatasetInstance.objects.get(
                    instance_id=output_dataset_instance_id
                )

                # Get the input datasset instance
                input_dataset_instance = dataset_models.DataSet

                # Create and save a TranslationPair object
                translation_pair_obj = dataset_models.TranslationPair(
                    parent_data=input_dataset_instance,
                    instance_id=output_dataset_instance,
                    input_language=language,
                    output_language=output_language,
                    input_text=input_sentence,
                    machine_translation=translated_sentence,
                    context=context,
                )
                translation_pair_obj.save()


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

    Steps being performed so far, can be removed once the workflow is finalized
    1. Check if the input dataset instance is a SentenceText dataset
    2. Check if it has "CorrectedText", if not then ask to export
    3. Check whether output ID and that it should be transaltion pair, then ask to create a new instance
    4. Iterate over all languages and use the api to get the target language translations
    5. Save the translation pair to the TranslationPair Datainstance
    """

    input_dataset_instance_id = request.data["input_dataset_instance_id"]
    languages = request.data["languages"]

    # Check if the input dataset instance is a SentenceText dataset
    try:
        input_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=input_dataset_instance_id
        )

        # Check if it's a sentence Text
        if input_dataset_instance.dataset_type != "SentenceText":
            return Response(
                {"message": "Input dataset instance is not a SentenceText dataset"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if corrected_text and quality_status are not null
        if (input_dataset_instance.corrected_text is None) or (
            input_dataset_instance.quality_status is None
        ):
            return Response(
                {"message": "The data has not been exported yet."},
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
        ).values_list("corrected_text", "language", "context", "quality_status")
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
            save_translation_pairs(
                languages,
                input_sentences,
                output_dataset_instance_id,
                input_dataset_instance_id,
            )

    except dataset_models.DatasetInstance.DoesNotExist:
        return Response(
            {
                "message": "Output dataset instance does not exist! Create a TranslationPair DatasetInstance"
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # return Response(get_translations_using_cdac_model("Hi, hello. What are you doing?", source_language='en', target_language='hi'))

    # Iterate over the input sentences and get the translations for the same
    output = []
    for sentences in input_sentences[:1]:

        result = get_translation_using_cdac_model(
            sentences[0], source_language=sentences[1], target_language=languages[0]
        )

        target_sentence = result.json()["output"][0]["target"]

        # Append the result to the output list
        output.append({"source": sentences[0], "target": target_sentence})

    ret_dict = {"message": "SUCCESS!", "result": output}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)
