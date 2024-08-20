import os
import re
from requests import RequestException
import requests
from dotenv import load_dotenv
from functions.tasks import update_meta_stats
from projects.utils import (
    no_of_words,
    get_audio_project_types,
    get_audio_transcription_duration,
    get_not_null_audio_transcription_duration,
)


Queued_Task_name = {
    "dataset.tasks.deduplicate_dataset_instance_items": "Deduplicate Dataset Instance Items",
    "dataset.tasks.upload_data_to_data_instance": "Upload Data to Dataset Instance",
    "functions.tasks.conversation_data_machine_translation": "Generate Machine Translations for Conversation Dataset",
    "functions.tasks.generate_asr_prediction_json": "Generate ASR Predictions for SpeechConversation Dataset",
    "functions.tasks.generate_ocr_prediction_json": "Generate OCR Prediction for OCR Document Dataset",
    "functions.tasks.populate_draft_data_json": "Populate Draft Data JSON",
    "functions.tasks.schedule_mail": "Mail Scheduled by User Profile",
    "functions.tasks.schedule_mail_for_project_reports": "Send Detailed Project Reports Mail",
    "functions.tasks.schedule_mail_to_download_all_projects": "Schedule Mail to Download All Projects",
    "functions.tasks.sentence_text_translate_and_save_translation_pairs": "Generate Machine Translations for Translation Pairs Dataset",
    "notifications.tasks.create_notification_handler": "Push Notification Created",
    "organizations.tasks.send_project_analytics_mail_org": "Send Project Analytics Mail At Organization Level",
    "organizations.tasks.send_user_analytics_mail_org": "Send User Analytics Mail At Organization Level",
    "organizations.tasks.send_user_reports_mail_org": "Send User Payment Reports Mail At Organization Level",
    "projects.tasks.add_new_data_items_into_project": "Add New Data Items into Project",
    "projects.tasks.create_parameters_for_task_creation": "Create Tasks for new Project",
    "projects.tasks.export_project_in_place": "Export Project In Place",
    "projects.tasks.export_project_new_record": "Export Project New Record",
    "send_mail_task": "Daily User Mails Scheduler",
    "send_user_reports_mail": "Send User Reports Mail ",
    "workspaces.tasks.send_project_analysis_reports_mail_ws": "Send Project Analysis Reports Mail At Workspace Level",
    "workspaces.tasks.send_user_analysis_reports_mail_ws": "Send User Analysis Reports Mail At Workspace Level",
    "workspaces.tasks.send_user_reports_mail_ws": "Send User Payment Reports Mail At Workspace Level",
}


def query_flower(filters=None):
    try:
        load_dotenv()
        address = os.getenv("FLOWER_ADDRESS")
        port = int(os.getenv("FLOWER_PORT"))
        flower_url = f"{address}:{port}"
        tasks_url = f"http://{flower_url}/api/tasks"
        flower_username = os.getenv("FLOWER_USERNAME")
        flower_password = os.getenv("FLOWER_PASSWORD")
        response = requests.get(tasks_url, auth=(flower_username, flower_password))

        if response.status_code == 200:
            all_tasks = response.json()
            filtered_tasks = {}

            if filters:
                # Apply filtering based on the provided filters
                for task_id, task in all_tasks.items():
                    if all(task.get(key) == value for key, value in filters.items()):
                        filtered_tasks[task_id] = task
            else:
                filtered_tasks = all_tasks

            return filtered_tasks
        elif response.status_code == 503:
            return {"error": "Service temporarily unavailable, check Flower"}
        else:
            return {"error": "Failed to retrieve tasks from Flower"}
    except RequestException as e:
        return {"error": f" failed to connect to flower API, {str(e)}"}


def compute_meta_stats_for_annotation(ann_obj, project_type):
    task_obj = ann_obj.task
    task_data = task_obj.data
    ced_project_type_choices = ["ContextualTranslationEditing"]
    result_meta_stats = {}
    result = ann_obj.result
    if project_type == "AcousticNormalisedTranscriptionEditing":
        (
            acousticNormalisedWordCount,
            verbatimWordCount,
            acousticNormalisedDuration,
            verbatimDuration,
        ) = (0, 0, 0, 0)
        for r in result:
            if r["from_name"] == "acoustic_normalised_transcribed_json":
                acousticNormalisedWordCount += calculateWordCount(ann_obj.result)
                acousticNormalisedDuration += calculateAudioDuration(ann_obj.result)
            elif r["from_name"] == "verbatim_transcribed_json":
                verbatimWordCount += calculateWordCount(ann_obj.result)
                verbatimDuration += calculateAudioDuration(ann_obj.result)
            # elif r["from_name"] == "transcribed_json":
        return {
            "acousticNormalisedWordCount": acousticNormalisedWordCount,
            "verbatimWordCount": verbatimWordCount,
            "acousticNormalisedDuration": acousticNormalisedDuration,
            "verbatimDuration": verbatimDuration,
        }
    elif project_type in ["AudioTranscription", "AudioTranscriptionEditing"]:
        wordCount, transcribedDuration = 0, 0
        for r in result:
            if r["from_name"] == "transcribed_json":
                wordCount += calculateWordCount(ann_obj.result)
                transcribedDuration += calculateAudioDuration(ann_obj.result)
        return {"wordCount": wordCount, "transcribedDuration": transcribedDuration}
    elif project_type in [
        "ContextualSentenceVerification",
        "ContextualSentenceVerificationAndDomainClassification",
        "ContextualTranslationEditing",
        "TranslationEditing",
    ]:
        wordCount = 0
        for r in result:
            if r["type"] == "textarea":
                wordCount += calculateWordCount(ann_obj.result)
        return {"wordCount": wordCount}
    elif project_type in [
        "ConversationTranslation",
        "ConversationTranslationEditing",
        "ConversationVerification",
    ]:
        wordCount, sentenceCount = 0, 0
        for r in result:
            if r["type"] == "textarea":
                wordCount += calculateWordCount(ann_obj.result)
                sentenceCount += calculateSentenceCount(
                    ann_obj.result["value"]["text"][0]
                )

        return {"wordCount": wordCount, "sentenceCount": sentenceCount}
    elif project_type in [
        "OCRTranscription",
        "OCRTranscriptionEditing",
        "OCRSegmentCategorizationEditing",
    ]:
        wordCount = 0
        for r in result:
            if r["from_name"] == "ocr_transcribed_json":
                wordCount += calculateWordCount(ann_obj.result)
        return {"wordCount": wordCount}


def calculateWordCount(annotation_result):
    word_count = 0
    try:
        word_count = no_of_words(annotation_result["value"]["text"][0])
    except:
        pass
    return word_count


def calculateAudioDuration(annotation_result):
    try:
        start = annotation_result["value"]["start"]
        end = annotation_result["value"]["end"]
    except:
        start, end = 0, 0
        pass
    return abs(end - start)


def calculateSentenceCount(text):
    sentences = re.split(r"[.!?]+", text)
    return len([sentence for sentence in sentences if sentence.strip()])
