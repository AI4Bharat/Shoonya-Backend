import json
import requests

from dataset import models as dataset_models
from dataset.serializers import SentenceTextSerializer
from projects.models import *
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from tasks.models import *

# from .utils import GoogleTranslator

## Utility functions
def get_translations_using_cdac_model(input_sentence, source_language, target_language):
    print("ENTER API")

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

    return response


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
        "output_dataset_instance_id": <int> [Optional]
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
        ).values_list("context", "language")
    )

    # Create a dataset instance for the output dataset
    output_dataset_instance_id = request.data.get("output_dataset_instance_id", 0)
    
    if output_dataset_instance_id: 
        # Check if the output type is TranslationPair
        pass 


    # return Response(get_translations_using_cdac_model("Hi, hello. What are you doing?", source_language='en', target_language='hi'))
    
    # Iterate over the input sentences and get the translations for the same
    output = []
    for sentences in input_sentences[:1]:

        result = get_translations_using_cdac_model(sentences[0], source_language=sentences[1], target_language=languages[0])

        target_sentence = result.json()["output"][0]['target']

        # Append the result to the output list
        output.append({"source": sentences[0], "target": target_sentence})
        



    ret_dict = {"message": "SUCCESS!", "result": output}
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)
