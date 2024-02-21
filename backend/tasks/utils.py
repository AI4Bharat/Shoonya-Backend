import os
from requests import RequestException
import requests
from dotenv import load_dotenv


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
