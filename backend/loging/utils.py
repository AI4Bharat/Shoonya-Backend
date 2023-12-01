import os
import requests
from dotenv import load_dotenv


def delete_elasticsearch_documents():
    load_dotenv()
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
    INDEX_NAME = os.getenv("INDEX_NAME")

    if not ELASTICSEARCH_URL or not INDEX_NAME:
        print(
            "Error: Ensure ELASTICSEARCH_URL and INDEX_NAME are defined in the .env file."
        )
    else:
        # Elasticsearch Delete By Query request
        url = f"{ELASTICSEARCH_URL}/{INDEX_NAME}/_delete_by_query?conflicts=proceed"
        headers = {"Content-Type": "application/json"}
        query = {"query": {"match_all": {}}}

        try:
            response = requests.post(url, headers=headers, json=query)
            response.raise_for_status()
            print("Documents deleted successfully.")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
