import ast
import json
from typing import Tuple
from dateutil.parser import parse as date_parse
import re
import nltk
from projects.models import Project
from rest_framework.response import Response
from rest_framework import status
from tasks.models import Annotation as Annotation_model
from users.models import User

from dataset.models import Instruction, Interaction
from tasks.models import Annotation, REVIEWER_ANNOTATION, SUPER_CHECKER_ANNOTATION
from tasks.views import SentenceOperationViewSet
import datetime
import yaml
from yaml.loader import SafeLoader
from jiwer import wer

from utils.convert_result_to_chitralekha_format import create_memory

nltk.download("punkt")


def get_audio_project_types():
    try:
        with open("projects/project_registry.yaml") as f:
            project_registry_details = yaml.load(f, Loader=SafeLoader)

        audio_project_types = project_registry_details["Audio"]["project_types"].keys()
    except Exception as e:
        return []
    return audio_project_types


def get_translation_dataset_project_types():
    try:
        with open("projects/project_registry.yaml") as f:
            project_registry_details = yaml.load(f, Loader=SafeLoader)

        translation_project_types = project_registry_details["Translation"][
            "project_types"
        ].keys()
    except Exception as e:
        return []
    return translation_project_types


def convert_seconds_to_hours(seconds):
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


# here this function  take input param  as string and  in   hh:mm:ss format (ex : 54:12:45)
def convert_hours_to_seconds(str1):
    hours_in_sec = int(str1.split(":")[0]) * 60 * 60
    min_in_sec = int(str1.split(":")[1]) * 60
    sec = int(str1.split(":")[2])
    return hours_in_sec + min_in_sec + sec


def no_of_words(string):
    if string == None:
        return 0
    list_words = nltk.tokenize.word_tokenize(string)
    list_tokens = [word for word in list_words if len(word) > 1]
    length_of_sent = len(list_tokens)
    return length_of_sent


def is_valid_date(s: str) -> Tuple[bool, str]:
    try:
        d = date_parse(s)
    except ValueError:
        return (
            False,
            "Invalid Date Format",
        )

    if d.date() > d.today().date():
        return (False, "Please select dates upto Today")

    return (True, "")


def conversation_wordcount(conversations: list) -> int:
    """
    Returns the total word count of the Conversation DatasetInstance type
    """
    word_count = 0
    if conversations == None:
        return word_count

    # Iterate through the list of dictionaries
    for conversation in conversations:
        for sentence in conversation["sentences"]:
            word_count += no_of_words(sentence)
    return word_count


def conversation_sentence_count(conversations: list) -> int:
    """
    Returns the total sentence count of the Conversation DatasetInstance type
    """
    if conversations == None:
        return 0
    return sum(len(conversation["sentences"]) for conversation in conversations)


def minor_major_accepted_task(annotation_objs):
    sentence_operation = SentenceOperationViewSet()

    minor, major = [], []
    for annot in annotation_objs:
        try:
            annotator_obj = Annotation.objects.get(
                task_id=annot.task_id, parent_annotation_id=None
            )
            reviewer_obj = Annotation.objects.filter(
                task_id=annot.task_id, parent_annotation_id__isnull=False
            )

            str1 = annotator_obj.result[0]["value"]["text"]
            str2 = reviewer_obj[0].result[0]["value"]["text"]
            data = {"sentence1": str1[0], "sentence2": str2[0]}

            char_level_distance = (
                sentence_operation.calculate_normalized_character_level_edit_distance(
                    data
                )
            )
            char_score = char_level_distance.data[
                "normalized_character_level_edit_distance"
            ]
            if char_score > 0.3:
                major.append(annot)
            else:
                minor.append(annot)
        except:
            pass

    return len(minor), len(major)


def get_audio_transcription_duration(annotation_result):
    audio_duration = 0
    for result in annotation_result:
        if result["type"] == "labels":
            start = result["value"]["start"]
            end = result["value"]["end"]
            audio_duration += abs(end - start)

    return audio_duration


def get_not_null_audio_transcription_duration(annotation_result, ann_id):
    audio_duration = 0
    memory = create_memory(annotation_result)
    for key, indexes in memory.items():
        if indexes["labels_dict_idx"] != -1 and indexes["text_dict_idx"] != -1:
            text_dict = annotation_result[indexes["text_dict_idx"]]
            label_dict = annotation_result[indexes["labels_dict_idx"]]
            if indexes["acoustic_text_dict_idx"] != -1:
                acoustic_dict = annotation_result[indexes["acoustic_text_dict_idx"]]
                if (
                    acoustic_dict["value"]["text"]
                    and len(acoustic_dict["value"]["text"][0]) <= 1
                ):
                    continue
            if text_dict["value"]["text"] and len(text_dict["value"]["text"][0]) <= 1:
                continue
            audio_duration += get_audio_transcription_duration([label_dict])
    return audio_duration


def get_audio_segments_count(annotation_result):
    count = 0
    for result in annotation_result:
        if result["type"] == "labels":
            count += 1

    return count


def calculate_word_error_rate_between_two_audio_transcription_annotation(
    annotation_result1, annotation_result2
):
    annotation_result1 = sorted(annotation_result1, key=lambda i: (i["value"]["end"]))
    annotation_result2 = sorted(annotation_result2, key=lambda i: (i["value"]["end"]))

    annotation_result1_text = ""
    annotation_result2_text = ""

    for result in annotation_result1:
        if result["from_name"] in ["transcribed_json", "verbatim_transcribed_json"]:
            try:
                for s in result["value"]["text"]:
                    annotation_result1_text += s
            except:
                pass

    for result in annotation_result2:
        if result["from_name"] in ["transcribed_json", "verbatim_transcribed_json"]:
            try:
                for s in result["value"]["text"]:
                    annotation_result2_text += s
            except:
                pass
    if len(annotation_result1_text) == 0 or len(annotation_result2_text) == 0:
        return 0
    return wer(annotation_result1_text, annotation_result2_text)


def ocr_word_count(annotation_result):
    word_count = 0

    for result in annotation_result:
        if result["type"] == "textarea":
            try:
                word_count += no_of_words(result["value"]["text"][0])
            except:
                pass

    return word_count


def get_attributes_for_IDC(project, task):
    correct_ann_obj = task.correct_annotation
    result_dict = {
        "interactions_json": correct_ann_obj.result,
        "language": project.tgt_language,
        "datetime": correct_ann_obj.annotated_at,
        "instruction_id": Instruction.objects.get(id=task.data["instruction_id"]),
        "time_taken": 0.0,
    }
    if correct_ann_obj.meta_stats and "number_of_turns" in correct_ann_obj.meta_stats:
        result_dict["no_of_turns"] = correct_ann_obj.meta_stats["number_of_turns"]
    return result_dict


def get_prompt_output_by_id(prompt_output_pair_id, task_data_dict):
    for interaction in task_data_dict.get("interactions_json", []):
        if interaction.get("prompt_output_pair_id") == prompt_output_pair_id:
            return interaction.get("prompt"), interaction.get("output")
    return None, None


def get_attributes_for_ModelInteractionEvaluation(task):
    res = []
    if task.correct_annotation:
        correct_ann_obj = task.correct_annotation
        annotation_result_json = correct_ann_obj.result
        interaction = Interaction.objects.get(id=task.data["interaction_id"])
    else:
        annotation_result_json = Annotation.objects.filter(task=task)[0].result
        annotation_result_json = (
            json.loads(annotation_result_json)
            if isinstance(annotation_result_json, str)
            else annotation_result_json
        )
        interaction = Interaction.objects.get(id=task.data["interaction_id"])
    for a in annotation_result_json:
        try:
            prompt_output_pair = get_prompt_output_by_id(
                a["prompt_output_pair_id"], task.data
            )
        except Exception as e:
            try:
                prompt_output_pair = [
                    annotation_result_json["prompt"],
                    annotation_result_json["output"],
                ]
            except Exception as e:
                prompt_output_pair = ["", ""]
        model = interaction.model
        language = interaction.language

        temp_attributes_obj = {
            "interaction_id": interaction,
            "model": model,
            "language": language,
            "prompt": prompt_output_pair[0],
            "output": prompt_output_pair[1],
        }
        if "prompt_output_pair_id" in a:
            temp_attributes_obj["prompt_output_pair_id"] = a["prompt_output_pair_id"]
        if "questions_response" in a:
            temp_attributes_obj["eval_form_output_json"] = a["questions_response"]
        if "time_taken" in a:
            temp_attributes_obj["eval_time_taken"] = a["time_taken"]
        res.append(temp_attributes_obj)

    return res


def assign_attributes_and_save_dataitem(
    annotation_fields, task_annotation_fields, data_item, task_data, task, project_type
):
    for field in annotation_fields:
        if field in task_data:
            setattr(data_item, field, task_data[field])
    for field in task_annotation_fields:
        if field in task_data:
            setattr(data_item, field, task_data[field])
    data_item.save()
    task.output_data = data_item
    task.save()


def get_user_from_query_params(
    request,
    user_type,
    pk,
):
    user_id_key = user_type + "_id"
    if user_id_key in dict(request.query_params).keys():
        user_id = request.query_params[user_id_key]
        project = Project.objects.get(pk=pk)
        user = User.objects.get(pk=user_id)
        workspace = project.workspace_id
        if request.user in workspace.managers.all():
            return user, None
        else:
            response = Response(
                {
                    "message": f"Only workspace managers can unassign tasks from other {user_type}s."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
            return None, response
    else:
        user = request.user
        return user, None


def get_status_from_query_params(request, status_type):
    status_key = status_type + "_status"
    if status_key in dict(request.query_params).keys():
        status_value = request.query_params[status_key]
        return ast.literal_eval(status_value)
    return None


def get_task_ids(request):
    try:
        task_ids = request.data.get("task_ids", None)
        return task_ids, None
    except Exception as e:
        return None, Response(
            {"message": f"Failed to get the task ids : {e}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


def get_annotations_for_project(
    flag, pk, user, status_value, task_ids, annotation_type
):
    project_id = pk
    if project_id:
        try:
            project_obj = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            final_result = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
            return None, Response(final_result, status=ret_status)
        if project_obj:
            ann = Annotation_model.objects.filter(
                task__project_id=project_id,
                annotation_type=annotation_type,
            )
            if flag == True:
                ann = ann.filter(
                    completed_by=user.id,
                    annotation_status__in=status_value,
                )
            elif task_ids != None:
                ann = ann.filter(task__id__in=task_ids)

            return ann, None
    return None, Response(
        {"message": "Project id not provided"}, status=status.HTTP_400_BAD_REQUEST
    )
