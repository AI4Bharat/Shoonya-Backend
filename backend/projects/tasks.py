import random
from urllib.parse import parse_qsl
from celery import shared_task

from users.models import User
from tasks.models import Task
from dataset import models as dataset_models
from tasks.models import *
from tasks.models import Annotation as Annotation_model
from .registry_helper import ProjectRegistry

from .models import *
from filters import filter
from utils.monolingual.sentence_splitter import split_sentences
from django.db.models import Count

## Utility functions for the tasks
def create_tasks_from_dataitems(items, project):
    project_type = project.project_type
    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
    output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)
    variable_parameters = project.variable_parameters

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
                item[output_field] = item[input_field]
                del item[input_field]
        data = dataset_models.DatasetBase.objects.get(pk=data_id)

        # Remove data id because it's not needed in task.data
        del item["id"]
        task = Task(data=item, project_id=project, input_data=data)
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

    # Load the dataset model from the instance id using the project registry
    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
    output_dataset_info = registry_helper.get_output_dataset_and_fields(project_type)

    dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])

    # Get items corresponding to the instance id
    data_items = dataset_model.objects.filter(
        instance_id__in=dataset_instance_ids
    ).order_by("id")

    # Apply filtering
    query_params = dict(parse_qsl(filter_string))
    query_params = filter.fix_booleans_in_dict(query_params)
    filtered_items = filter.filter_using_dict_and_queryset(query_params, data_items)

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
    label_config = registry_helper.get_label_studio_jsx_payload(project_type)

    project.label_config = label_config
    project.save()

    # Create Tasks from Parameters
    create_tasks_from_dataitems(sampled_items, project)

@shared_task
def assign_project_tasks(project_id, user_id, task_count):
    project = Project.objects.get(pk=project_id)

    # get all unlabeled tasks for this project along with count for annotators assigned to each task
    tasks_query = Task.objects.filter(project_id=project_id).filter(task_status=UNLABELED).annotate(annotator_count=Count("annotation_users"))

    # filter out tasks which meet the annotator count threshold
    # and assign the ones with least count to user, so as to maintain uniformity
    tasks_query = tasks_query.filter(annotator_count__lt=project.required_annotators_per_task).order_by('annotator_count')[:task_count]
    user_obj = User.objects.get(pk=user_id)
    for task in tasks_query:
        task.annotation_users.add(user_obj)
        task.save()