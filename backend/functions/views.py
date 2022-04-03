from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from dataset import models as dataset_models
from projects.models import *
from tasks.models import Task
import json

@api_view(['POST'])
def copy_from_block_text_to_sentence_text(request):
    """
    List all code snippets, or create a new snippet.
    """
    export_dataset_instance_id = request.data['export_dataset_instance_id']
    project_id = request.data['project_id']
    project = Project.objects.get(pk=project_id)

    if project.is_archived == False:
        ret_dict = {"message": "Project is not archived!"}         
        ret_status = status.HTTP_403_FORBIDDEN
        return Response(ret_dict, status=ret_status)

    if project.metadata_json is None:
        project.metadata_json = {}
    if "copy_from_block_text_to_sentence_text" in project.metadata_json:
        ret_dict = {"message": "Function already applied on this project!"}         
        ret_status = status.HTTP_403_FORBIDDEN
        return Response(ret_dict, status=ret_status)

    export_dataset_instance = dataset_models.DatasetInstance.objects.get(instance_id__exact=export_dataset_instance_id)
    # dataset_model = dataset_models.BlockText
    # input_instances = project.dataset_id
    tasks = Task.objects.filter(project_id__exact=project)
    all_sentence_texts = []
    for task in tasks:
        # TODO: Create child object from parent to optimize query
        if task.output_data is not None:
            block_text = dataset_models.BlockText.objects.get(data_id=task.output_data.data_id)
            # block_text = task.output_data
            # print(block_text)
            # block_text.__class__ = dataset_models.BlockText
            # block_text = dataset_models.BlockText()
            # block_text = task.output_data
            raw_text = block_text.splitted_text
            sentences = raw_text.split("\n")
            for sentence in sentences:
                sentence_text = dataset_models.SentenceText(
                    lang_id=block_text.lang_id,
                    text=sentence,
                    domain=block_text.domain,
                    instance_id = export_dataset_instance,
                )
                all_sentence_texts.append(sentence_text)


    # TODO: implement bulk create if possible (only if non-hacky)
    for sentence_text in all_sentence_texts:
        sentence_text.save()
    # dataset_models.SentenceText.objects.bulk_create(all_sentence_texts)
    
    project.metadata_json["copy_from_block_text_to_sentence_text"]=True
    project.save()
    ret_dict = {"message": "SUCCESS!"}         
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)


@api_view(['POST'])
def copy_from_ocr_document_to_block_text(request):
    """
    List all code snippets, or create a new snippet.
    """
    export_dataset_instance_id = request.data['export_dataset_instance_id']
    project_id = request.data['project_id']
    project = Project.objects.get(pk=project_id)

    if project.is_archived == False:
        ret_dict = {"message": "Project is not archived!"}         
        ret_status = status.HTTP_403_FORBIDDEN
        return Response(ret_dict, status=ret_status)

    if project.metadata_json is None:
        project.metadata_json = {}
    if "copy_from_ocr_document_to_block_text" in project.metadata_json:
        ret_dict = {"message": "Function already applied on this project!"}         
        ret_status = status.HTTP_403_FORBIDDEN
        return Response(ret_dict, status=ret_status)

    export_dataset_instance = dataset_models.DatasetInstance.objects.get(instance_id__exact=export_dataset_instance_id)
    # dataset_model = dataset_models.BlockText
    # input_instances = project.dataset_id
    tasks = Task.objects.filter(project_id__exact=project)
    all_block_texts = []
    for task in tasks:
        # TODO: Create child object from parent to optimize query
        if task.output_data is not None:
            ocr_document = dataset_models.OCRDocument.objects.get(data_id=task.output_data.data_id)
            # block_text = task.output_data
            # print(block_text)
            # block_text.__class__ = dataset_models.BlockText
            # block_text = dataset_models.BlockText()
            # block_text = task.output_data
            transcriptions = ocr_document.annotation_transcripts
            transcriptions = json.loads(transcriptions)

            labels = ocr_document.annotation_labels
            labels = json.loads(labels)

            body_transcriptions = []
            for i,label in enumerate(labels):
                if label['labels'][0] == 'Body':
                    body_transcriptions.append(transcriptions[i])

            text = " ".join(body_transcriptions)
            # TODO: check if domain can be same as OCR domain
            block_text = dataset_models.BlockText(
                lang_id=ocr_document.lang_id,
                text=text,
                domain=ocr_document.ocr_domain,
                instance_id = export_dataset_instance,
            )
            all_block_texts.append(block_text)


    # TODO: implement bulk create if possible (only if non-hacky)
    for block_text in all_block_texts:
        block_text.save()
    # dataset_models.SentenceText.objects.bulk_create(all_sentence_texts)
    
    project.metadata_json["copy_from_ocr_document_to_block_text"]=True
    project.save()
    ret_dict = {"message": "SUCCESS!"}         
    ret_status = status.HTTP_200_OK
    return Response(ret_dict, status=ret_status)





