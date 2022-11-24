import random
from collections import OrderedDict
from urllib.parse import parse_qsl

from celery import shared_task
from celery.utils.log import get_task_logger
from dataset import models as dataset_models
from django.forms.models import model_to_dict
from filters import filter
from users.models import User

from tasks.models import Annotation as Annotation_model
from tasks.models import *
from tasks.models import Task
from utils.monolingual.sentence_splitter import split_sentences

from .models import *
from .registry_helper import ProjectRegistry
from .utils import conversation_wordcount, no_of_words, conversation_sentence_count

# Celery logger settings
logger = get_task_logger(__name__)


## Utility functions for the tasks
def create_tasks_from_dataitems(items, project):
    project_type = project.project_type
    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
    output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)
    variable_parameters = project.variable_parameters
    project_type_lower = project_type.lower()
    is_translation_project = "translation" in project_type_lower
    is_conversation_project = "conversation" in project_type_lower
    is_editing_project = "editing" in project_type_lower

    # Create task objects
    tasks = []
    for item in items:
        data_id = item["id"]
        if "variable_parameters" in output_dataset_info["fields"]:
            for var_param in output_dataset_info["fields"]["variable_parameters"]:
                item[var_param] = variable_parameters[var_param]
        if "copy_from_input" in output_dataset_info["fields"]:
            for input_field, output_field in output_dataset_info["fields"][
                "copy_from_input"
            ].items():
                if output_field == input_field:
                    continue
                item[output_field] = item[input_field]
                del item[input_field]
        if "copy_from_parent" in input_dataset_info:
            if not item.get("parent_data"):
                raise Exception("Item does not have a parent")
            try:
                # get the parent class from the registry and get the parent object
                parent_class = input_dataset_info["parent_class"]
                parent_data = model_to_dict(
                    getattr(dataset_models, parent_class).objects.get(
                        id=item["parent_data"]
                    )
                )
                for input_field, output_field in input_dataset_info[
                    "copy_from_parent"
                ].items():
                    item[output_field] = parent_data[input_field]
            except dataset_models.DatasetBase.DoesNotExist:
                raise Exception("Parent data not found")
        data = dataset_models.DatasetBase.objects.get(pk=data_id)

        # Remove data id because it's not needed in task.data
        del item["id"]
        task = Task(data=item, project_id=project, input_data=data)
        if is_translation_project:
            if is_conversation_project:
                field_name = (
                    "source_conversation_json"
                    if is_editing_project
                    else "conversation_json"
                )
                task.data["word_count"] = conversation_wordcount(task.data[field_name])
                task.data["sentence_count"] = conversation_sentence_count(
                    task.data[field_name]
                )
            else:
                task.data["word_count"] = no_of_words(task.data["input_text"])
        tasks.append(task)
    # Bulk create the tasks
    Task.objects.bulk_create(tasks)

    if input_dataset_info["prediction"] is not None:
        user_object = User.objects.get(email="prediction@ai4bharat.org")

        predictions = []
        prediction_field = input_dataset_info["prediction"]
        for task, item in zip(tasks, items):

            if project_type == "SentenceSplitting":
                item[prediction_field] = [
                    {
                        "value": {
                            "text": [
                                "\n".join(
                                    split_sentences(item["text"], item["language"])
                                )
                            ]
                        },
                        "id": "0",
                        "from_name": "splitted_text",
                        "to_name": "text",
                        "type": "textarea",
                    }
                ]
            prediction = Annotation_model(
                result=item[prediction_field], task=task, completed_by=user_object
            )
            predictions.append(prediction)
        #
        # Prediction.objects.bulk_create(predictions)
        Annotation_model.objects.bulk_create(predictions)
    return tasks


def filter_data_items(
    project_type, dataset_instance_ids, filter_string, ids_to_exclude=None
):
    """Function to apply filtering for tasks.

    Args:
        project_type (str): Describes the type of project passed by the user
        dataset_instance_ids (int): ID of the dataset that has been provided for the annotation task
        filter_string (str): _description_
        ids_to_exclude(list): List of ids that need to be filtered(excluded) from the result
    """

    # Load the dataset model from the instance id using the project registry
    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)

    dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])

    # Get items corresponding to the instance id
    data_items = dataset_model.objects.filter(
        instance_id__in=dataset_instance_ids
    ).order_by("id")

    # Apply filtering
    query_params = dict(parse_qsl(filter_string, keep_blank_values=True))
    query_params = filter.fix_booleans_in_dict(query_params)
    filtered_items = filter.filter_using_dict_and_queryset(query_params, data_items)

    # Create tasks from the filtered items
    if ids_to_exclude is not None:
        filtered_items = filtered_items.exclude(
            id__in=ids_to_exclude.values("input_data")
        )
    # Get the input dataset fields from the filtered items
    if input_dataset_info["prediction"] is not None:
        filtered_items = list(
            filtered_items.values(
                "id", *input_dataset_info["fields"], input_dataset_info["prediction"]
            )
        )
    else:
        filtered_items = list(
            filtered_items.values("id", *input_dataset_info["fields"])
        )
    return filtered_items


#### CELERY SHARED TASKS


@shared_task
def create_parameters_for_task_creation(
    project_type,
    dataset_instance_ids,
    filter_string,
    sampling_mode,
    sampling_parameters,
    variable_parameters,
    project_id,
) -> None:
    """Function to create the paramters for the task creation process. The function is passed arguments from the frontend which decide how the sentences have to be filtered and sampled.

    Args:
        project_type (str): Describes the type of project passed by the user
        dataset_instance_ids (int): ID of the dataset that has been provided for the annotation task
        filter_string (str): _description_
        sampling_mode (str): Method of sampling
        sampling_parameters (dict): Parameters for sampling
        variable_parameters (dict): _description_
        project_id (int): ID of the project object created in this iteration

    """

    filtered_items = filter_data_items(
        project_type, dataset_instance_ids, filter_string
    )

    # Apply sampling
    if sampling_mode == RANDOM:
        try:
            sampling_count = sampling_parameters["count"]
        except KeyError:
            sampling_fraction = sampling_parameters["fraction"]
            sampling_count = int(sampling_fraction * len(filtered_items))
        sampled_items = random.sample(filtered_items, k=sampling_count)
    elif sampling_mode == BATCH:
        batch_size = sampling_parameters["batch_size"]
        try:
            batch_number = sampling_parameters["batch_number"]
        except KeyError:
            batch_number = 1
        sampled_items = filtered_items[
            batch_size * (batch_number - 1) : batch_size * (batch_number)
        ]
    else:
        sampled_items = filtered_items
    # Load the project object using the project id
    project = Project.objects.get(pk=project_id)

    # Set the labelstudio label config
    registry_helper = ProjectRegistry.get_instance()
    label_config = registry_helper.get_label_studio_jsx_payload(project_type)

    project.label_config = label_config
    project.save()

    # Create Tasks from Parameters
    create_tasks_from_dataitems(sampled_items, project)


@shared_task
def export_project_in_place(
    annotation_fields, project_id, project_type, get_request_data
) -> None:
    """Function to export the output texts for a task into the dataset instance

    Args:
        annotation_fields (list): List of annotated fields to be exported
        project_id (int): ID of the project to which the tasks belong
        project_type (str): Type of project
        get_request_data (dict): Dictionary of the GET request data
    """

    # Read registry to get output dataset model, and output fields
    registry_helper = ProjectRegistry.get_instance()
    output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)

    dataset_model = getattr(dataset_models, output_dataset_info["dataset_type"])

    # Get project object
    project = Project.objects.get(pk=project_id)

    # Get all the accepted tasks for the project
    tasks = Task.objects.filter(
        project_id__exact=project, task_status__in=[ACCEPTED, ACCEPTED_WITH_CHANGES]
    )

    data_items = []

    # List for storing tasks fetched with modified data to the task_dict
    tasks_list = []

    # List for storing the annotated tasks that have been accepted as correct annotation
    annotated_tasks = []
    for task in tasks:
        task_dict = model_to_dict(task)
        # Rename keys to match label studio converter
        # task_dict['id'] = task_dict['task_id']
        # del task_dict['task_id']
        if task.correct_annotation is not None:
            annotated_tasks.append(task)
            annotation_dict = model_to_dict(task.correct_annotation)
            # annotation_dict['result'] = annotation_dict['result_json']
            # del annotation_dict['result_json']
            task_dict["annotations"] = [OrderedDict(annotation_dict)]
        del task_dict["annotation_users"]
        del task_dict["review_user"]
        tasks_list.append(OrderedDict(task_dict))
    download_resources = True
    tasks_df = DataExport.export_csv_file(
        project, tasks_list, download_resources, get_request_data
    )
    tasks_annotations = json.loads(tasks_df.to_json(orient="records"))

    for (ta, tl, task) in zip(tasks_annotations, tasks_list, annotated_tasks):

        if output_dataset_info["dataset_type"] == "SpeechConversation":
            ta_labels = json.loads(ta["labels"])
            ta_transcribed_json = json.loads(ta["transcribed_json"])
        task.output_data = task.input_data
        task.save()
        data_item = dataset_model.objects.get(id__exact=tl["input_data"])
        for field in annotation_fields:
            # Check being done for rating as Label studio stores all the data in string format
            # We need to store the rating in integer format
            if field == "rating":
                setattr(data_item, field, int(ta[field]))
            elif field == "transcribed_json":
                speakers_details = json.loads(data_item.speakers_json)
                for idx in range(len(ta_transcribed_json)):
                    ta_labels[idx]["text"] = ta_transcribed_json[idx]
                    speaker_id = next(
                        speaker
                        for speaker in speakers_details
                        if speaker["name"] == ta_labels[idx]["labels"][0]
                    )["speaker_id"]
                    ta_labels[idx]["speaker_id"] = speaker_id
                    del ta_labels[idx]["labels"]
                ta_labels = json.dumps(ta_labels)
                setattr(data_item, field, ta_labels)
            else:
                setattr(data_item, field, ta[field])
        data_items.append(data_item)
    # Write json to dataset columns
    dataset_model.objects.bulk_update(data_items, annotation_fields)

    return f"Exported {len(data_items)} items."


@shared_task
def export_project_new_record(
    annotation_fields,
    project_id,
    project_type,
    export_dataset_instance_id,
    task_annotation_fields,
    get_request_data,
) -> None:
    """_summary_

    Args:
        annotation_fields (list): List of annotated fields to be exported
        project_id (int): ID of the project to which the tasks belong
        project_type (str): Type of project
        export_dataset_instance_id (int):ID of the dataset where the export is happening
        task_annotation_fields (list): List of annotated task
        get_request_data (dict): Dictionary of the GET request data
    """

    # Read registry to get output dataset model, and output fields
    registry_helper = ProjectRegistry.get_instance()
    output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)

    dataset_model = getattr(dataset_models, output_dataset_info["dataset_type"])

    # Get the export dataset instance
    export_dataset_instance = dataset_models.DatasetInstance.objects.get(
        instance_id__exact=export_dataset_instance_id
    )

    # Get project object
    project = Project.objects.get(pk=project_id)

    # Get all the accepted tasks for the project
    tasks = Task.objects.filter(
        project_id__exact=project, task_status__in=[ACCEPTED, ACCEPTED_WITH_CHANGES]
    )

    tasks_list = []
    annotated_tasks = []
    for task in tasks:
        task_dict = model_to_dict(task)
        # Rename keys to match label studio converter
        # task_dict['id'] = task_dict['task_id']
        # del task_dict['task_id']
        if project.project_mode == Annotation:
            if task.correct_annotation is not None:
                annotated_tasks.append(task)
                annotation_dict = model_to_dict(task.correct_annotation)
                # annotation_dict['result'] = annotation_dict['result_json']
                # del annotation_dict['result_json']
                task_dict["annotations"] = [OrderedDict(annotation_dict)]
        elif project.project_mode == Collection:
            annotated_tasks.append(task)
        del task_dict["annotation_users"]
        del task_dict["review_user"]
        tasks_list.append(OrderedDict(task_dict))
    if project.project_mode == Collection:
        for (tl, task) in zip(tasks_list, annotated_tasks):
            if task.output_data is not None:
                data_item = dataset_model.objects.get(id__exact=task.output_data.id)
            else:
                data_item = dataset_model()
                data_item.instance_id = export_dataset_instance
            for field in annotation_fields:
                setattr(data_item, field, tl["data"][field])
            for field in task_annotation_fields:
                setattr(data_item, field, tl["data"][field])
            data_item.save()
            task.output_data = data_item
            task.save()
    elif project.project_mode == Annotation:

        download_resources = True
        # export_stream, content_type, filename = DataExport.generate_export_file(
        #     project, tasks_list, 'CSV', download_resources, request.GET
        # )

        tasks_df = DataExport.export_csv_file(
            project, tasks_list, download_resources, get_request_data
        )
        tasks_annotations = json.loads(tasks_df.to_json(orient="records"))

        for (ta, task) in zip(tasks_annotations, annotated_tasks):
            # data_item = dataset_model.objects.get(id__exact=task.id.id)
            if task.output_data is not None:
                data_item = dataset_model.objects.get(id__exact=task.output_data.id)
            else:
                data_item = dataset_model()
                data_item.instance_id = export_dataset_instance
                data_item.parent_data = task.input_data
            for field in annotation_fields:
                setattr(data_item, field, ta[field])
            for field in task_annotation_fields:
                setattr(data_item, field, ta[field])
            data_item.save()
            task.output_data = data_item
            task.save()


@shared_task
def add_new_data_items_into_project(project_id, items):
    """Function to pull the dataitems into the project

    Args:
        project_id (int): ID of the project where the new data items have to be pulled
        items (list) : List of items to be pulled into the project
    """

    # Get project instance
    project = Project.objects.get(pk=project_id)
    new_tasks = create_tasks_from_dataitems(items, project)

    return f"Pulled {len(new_tasks)} new data items into project {project.title}"
