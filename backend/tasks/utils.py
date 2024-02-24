import json
import os
from requests import RequestException
import requests
from dotenv import load_dotenv


def compute_meta_stats_for_instruction_driven_chat(conversation_history):
    """
    Calculate meta stats for instruction-driven chat.

    Args:
        conversation_history (list): List of dicts, each containing 'prompt' and 'output'.

    Returns:
        dict: Meta statistics JSON with 'prompts_word_count' and 'number_of_turns'.
    """
    conversation_history = (
        json.loads(conversation_history)
        if isinstance(conversation_history, str)
        else conversation_history
    )
    number_of_words = sum(
        len(entry["prompt"].split()) for entry in conversation_history
    )
    number_of_turns = len(conversation_history)

    meta_stats = {
        "prompts_word_count": number_of_words,
        "number_of_turns": number_of_turns,
    }

    return meta_stats


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
