import os
import re
from requests import RequestException
import requests
from dotenv import load_dotenv
from projects.utils import (
    no_of_words,
    get_audio_project_types,
    get_audio_transcription_duration,
    get_not_null_audio_transcription_duration,
    calculate_word_error_rate_between_two_audio_transcription_annotation,
)
from tasks.models import Annotation, REVIEWER_ANNOTATION, ANNOTATOR_ANNOTATION, SUPER_CHECKER_ANNOTATION, ACCEPTED, ACCEPTED_WITH_MINOR_CHANGES, ACCEPTED_WITH_MAJOR_CHANGES, VALIDATED, VALIDATED_WITH_CHANGES


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
    from tasks.views import SentenceOperationViewSet
    task_obj = ann_obj.task
    task_data = task_obj.data
    ced_project_type_choices = ["ContextualTranslationEditing"]
    result_meta_stats = {}
    result = ann_obj.result

    # calculating wer and bleu scores
    all_annotations = Annotation.objects.filter(task_id=task_obj.id)
    ar_wer_score, as_wer_score, rs_wer_score = 0, 0, 0
    ar_bleu_score, rs_bleu_score = 0, 0
    ar_done, as_done, rs_done = False, False, False
    ann_ann, rev_ann, sup_ann = "", "", ""
    for a in all_annotations:
        if a.annotation_type == REVIEWER_ANNOTATION and a.annotation_status in [
            ACCEPTED,
            ACCEPTED_WITH_MINOR_CHANGES,
            ACCEPTED_WITH_MAJOR_CHANGES,
        ]:
            rev_ann = a
        elif (
                a.annotation_type == SUPER_CHECKER_ANNOTATION
                and a.annotation_status in [VALIDATED, VALIDATED_WITH_CHANGES]
        ):
            sup_ann = a
        elif a.annotation_type == ANNOTATOR_ANNOTATION:
            ann_ann = a
        if ann_ann and rev_ann and not ar_done:
            try:
                ar_wer_score += calculate_word_error_rate_between_two_audio_transcription_annotation(
                    rev_ann.result, ann_ann.result, project_type
                )
                ar_done = True
            except Exception as e:
                pass
            try:
                s1 = SentenceOperationViewSet()
                sampleRequest = {
                    "annotation_result1": rev_ann.result,
                    "annotation_result2": ann_ann.result,
                }
                ar_bleu_score += float(
                    s1.calculate_bleu_score(sampleRequest).data["ar_bleu_score"]
                )
            except Exception as e:
                pass
        if rev_ann and sup_ann and not rs_done:
            try:
                rs_wer_score += calculate_word_error_rate_between_two_audio_transcription_annotation(
                    sup_ann.result, rev_ann.result, project_type
                )
                rs_done = True
            except Exception as e:
                pass
            try:
                s1 = SentenceOperationViewSet()
                sampleRequest = {
                    "annotation_result1": sup_ann.result,
                    "annotation_result2": rev_ann.result,
                }
                rs_bleu_score += float(
                    s1.calculate_bleu_score(sampleRequest).data["rs_bleu_score"]
                )
            except Exception as e:
                pass
        if ann_ann and sup_ann and not as_done:
            meta_stats = sup_ann.meta_stats
            if "as_wer_score" in meta_stats:
                as_wer_score += meta_stats["as_wer_score"]
                as_done = True
            try:
                as_wer_score += calculate_word_error_rate_between_two_audio_transcription_annotation(
                    sup_ann.result, ann_ann.result, project_type
                )
                as_done = True
            except Exception as e:
                pass

    if project_type == "AcousticNormalisedTranscriptionEditing":
        (
            acoustic_normalised_word_count,
            verbatim_word_count,
            acoustic_normalised_duration,
            verbatim_duration,
        ) = (0, 0, 0, 0)
        for r in result:
            if r["from_name"] == "acoustic_normalised_transcribed_json":
                acoustic_normalised_word_count += calculateWordCount(ann_obj.result)
                acoustic_normalised_duration += calculateAudioDuration(ann_obj.result)
            elif r["from_name"] == "verbatim_transcribed_json":
                verbatim_word_count += calculateWordCount(ann_obj.result)
                verbatim_duration += calculateAudioDuration(ann_obj.result)
        segment_duration = get_audio_transcription_duration(result)
        not_null_segment_duration = get_not_null_audio_transcription_duration(result)
        return {
            "acoustic_normalised_word_count": acoustic_normalised_word_count,
            "verbatim_word_count": verbatim_word_count,
            "acoustic_normalised_duration": acoustic_normalised_duration,
            "verbatim_duration": verbatim_duration,
            "total_segment_duration": segment_duration,
            "not_null_segment_duration": not_null_segment_duration,
            "ar_wer_score": ar_wer_score,
            "as_wer_score": as_wer_score,
            "rs_wer_score": rs_wer_score,
            "ar_bleu_score": ar_bleu_score,
            "rs_bleu_score": rs_bleu_score
        }
    elif project_type in ["AudioTranscription", "AudioTranscriptionEditing"]:
        transcribed_word_count, transcribed_duration = 0, 0
        for r in result:
            if r["from_name"] == "transcribed_json":
                transcribed_word_count += calculateWordCount(ann_obj.result)
                transcribed_duration += calculateAudioDuration(ann_obj.result)
        segment_duration = get_audio_transcription_duration(result)
        not_null_segment_duration = get_not_null_audio_transcription_duration(result)
        return {"audio_word_count": transcribed_word_count,
                "transcribed_duration": transcribed_duration,
                "total_segment_duration": segment_duration,
                "not_null_segment_duration": not_null_segment_duration,
                "ar_wer_score": ar_wer_score,
                "as_wer_score": as_wer_score,
                "rs_wer_score": rs_wer_score,
                "ar_bleu_score": ar_bleu_score,
                "rs_bleu_score": rs_bleu_score
                }
    elif project_type in [
        "ContextualSentenceVerification",
        "ContextualSentenceVerificationAndDomainClassification",
        "ContextualTranslationEditing",
        "TranslationEditing",
    ]:
        word_count = 0
        for r in result:
            if r["type"] == "textarea":
                word_count += calculateWordCount(ann_obj.result)
        return {"word_count": word_count,
                "ar_wer_score": ar_wer_score,
                "as_wer_score": as_wer_score,
                "rs_wer_score": rs_wer_score,
                "ar_bleu_score": ar_bleu_score,
                "rs_bleu_score": rs_bleu_score
                }
    elif project_type in [
        "ConversationTranslation",
        "ConversationTranslationEditing",
        "ConversationVerification",
    ]:
        word_count, sentence_count = 0, 0
        for r in result:
            if r["type"] == "textarea":
                word_count += calculateWordCount(ann_obj.result)
                sentence_count += calculateSentenceCount(
                    ann_obj.result["value"]["text"][0]
                )

        return {"word_count": word_count,
                "sentence_count": sentence_count,
                "ar_wer_score": ar_wer_score,
                "as_wer_score": as_wer_score,
                "rs_wer_score": rs_wer_score,
                "ar_bleu_score": ar_bleu_score,
                "rs_bleu_score": rs_bleu_score
                }
    elif project_type in [
        "OCRTranscription",
        "OCRTranscriptionEditing",
        "OCRSegmentCategorizationEditing",
    ]:
        word_count = 0
        for r in result:
            if r["from_name"] == "ocr_transcribed_json":
                word_count += calculateWordCount(ann_obj.result)
        return {"word_count": word_count,
                "ar_wer_score": ar_wer_score,
                "as_wer_score": as_wer_score,
                "rs_wer_score": rs_wer_score,
                "ar_bleu_score": ar_bleu_score,
                "rs_bleu_score": rs_bleu_score
                }


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
