from typing import Tuple
from dateutil.parser import parse as date_parse
import re
import nltk

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
    with open("projects/project_registry.yaml") as f:
        project_registry_details = yaml.load(f, Loader=SafeLoader)

    audio_project_types = project_registry_details["Audio"]["project_types"].keys()
    return audio_project_types


def get_translation_dataset_project_types():
    with open("projects/project_registry.yaml") as f:
        project_registry_details = yaml.load(f, Loader=SafeLoader)

    translation_project_types = project_registry_details["Translation"][
        "project_types"
    ].keys()
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

#function to obtain the correct annotation object
def get_correct_annotation_obj(task):
    annotation = Annotation.objects.filter(task=task)
    correct_ann_obj = annotation[0]
    if len(annotation) == 2:
        for ann in annotation:
            if ann.annotation_type == REVIEWER_ANNOTATION:
                correct_ann_obj = ann
    elif len(annotation) == 3:
        for ann in annotation:
            if ann.annotation_type == SUPER_CHECKER_ANNOTATION:
                correct_ann_obj = ann
    return correct_ann_obj

def get_attributes_for_IDC(project, task):
    correct_ann_obj = get_correct_annotation_obj(task)
    return {
        "interactions_json": correct_ann_obj.result,
        "no_of_turns": correct_ann_obj.meta_stats["number_of_turns"],
        "language": project.tgt_language,
        "datetime": correct_ann_obj.annotated_at,
        "instruction_id": Instruction.objects.get(id=task.data["instruction_id"]),
        "time_taken": 0.0,
    }

def get_prompt_output_by_id(prompt_output_pair_id,task_data_dict):
    for interaction in task_data_dict.get("interactions_json", []):
        if interaction.get("prompt_output_pair_id") == prompt_output_pair_id:
            return interaction.get("prompt"), interaction.get("output")
    return None, None


def get_attributes_for_ModelInteractionEvaluation(task):
    correct_ann_obj = get_correct_annotation_obj(task)
    res = []
    annotation_result_json = correct_ann_obj.result

    interaction_id = Interaction.objects.get(id=task.data["interaction_id"])
    
    model = interaction_id.model
    language = interaction_id.language
    for obj in annotation_result_json:
        prompt_output_pair = get_prompt_output_by_id(obj["prompt_output_pair_id"],task.data)
        temp_attributes_obj = {
            "interaction_id":interaction_id,
            "eval_form_output_json":obj['form_output_json'],
            "eval_output_likert_score":obj['output_likert_score'],
            "eval_time_taken":obj['time_taken'],
            "model":model,
            "language":language,
            "prompt":prompt_output_pair[0],
            "output":prompt_output_pair[1],
        }
        print(temp_attributes_obj)
        res.append(temp_attributes_obj)

    return res

def assign_attributes_and_save_dataitem(annotation_fields,task_annotation_fields,data_item,task_data,task,project_type):
    for field in annotation_fields:
        setattr(data_item, field, task_data[field])
    for field in task_annotation_fields:
        setattr(data_item, field, task_data[field])
    if project_type=="ModelInteractionEvaluation":
        setattr(data_item, "prompt", task_data["prompt"])
        setattr(data_item, "output", task_data["output"])
        setattr(data_item, "model", task_data["model"])
        setattr(data_item, "language", task_data["language"])
    data_item.save()
    task.output_data = data_item
    task.save()

