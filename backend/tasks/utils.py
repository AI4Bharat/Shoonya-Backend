import os
from requests import RequestException
import requests
from dotenv import load_dotenv
import base64
import subprocess
import io


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
    

def convert_audio_base64_to_mp3(input_base64):
    """Convert base64 audio to MP3 format"""
    try:
        input_audio_bytes = base64.b64decode(input_base64)
        input_buffer = io.BytesIO(input_audio_bytes)

        ffmpeg_command = ["ffmpeg", "-i", "pipe:0", "-f", "mp3", "pipe:1"]

        process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        output_mp3_bytes, _ = process.communicate(input=input_buffer.read())
        return base64.b64encode(output_mp3_bytes).decode("utf-8")

    except Exception as e:
        print(f"Audio conversion error: {e}")
        return None


def transcribe_audio(audio_base64, lang="hi"):
    """Send audio to Dhruva ASR API"""
    try:
        mp3_base64 = convert_audio_base64_to_mp3(audio_base64)
        if not mp3_base64:
            return None

        payload = {
            "config": {
                "serviceId": os.getenv("DHRUVA_SERVICE_ID"),
                "language": {"sourceLanguage": lang},
                "transcriptionFormat": {"value": "transcript"},
            },
            "audio": [{"audioContent": mp3_base64}],
        }

        response = requests.post(
            os.getenv("DHRUVA_API_URL"),
            headers={"Authorization": os.getenv("DHRUVA_KEY")},
            json=payload,
        )

        return response.json()["output"][0]["source"]

    except Exception as e:
        print(f"Transcription failed: {e}")
        return None
