import os
import numpy as np
import json
import ast
import openai
import requests

from dataset.models import Interaction
from tasks.models import Annotation


def get_response_for_domain_and_intent(prompt):
    openai.api_key = os.getenv("LLM_CHECKS_OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        engine="prompt-chat-gpt35",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=256,
        # top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    return response["choices"][0]["message"]["content"]


def get_lid(text):
    """
    Determine the language and script of the given text using the IndicLID model.
    """

    # The inference server URL
    TRITON_SERVER_URL = os.getenv("LLM_CHECKS_TRITON_SERVER_URL")

    # Authentication header
    headers = {
        "Authorization": os.getenv("LLM_CHECKS_TRITON_SERVER_URL_AUTH"),
        "Content-Type": "application/json",
    }

    # Prepare the input data
    input_data = np.array([[text]], dtype=object).tolist()

    # Prepare the request body
    body = json.dumps(
        {
            "inputs": [
                {
                    "name": "TEXT",
                    "shape": [1, 1],
                    "datatype": "BYTES",
                    "data": input_data,
                }
            ],
            "outputs": [{"name": "LANGUAGES"}],
        }
    )

    # Make the request
    response = requests.post(TRITON_SERVER_URL, headers=headers, data=body)

    # Check if the request was successful
    if response.status_code != 200:
        print("Error during inference request:", response.text)
        return None

    # Extract results from the response
    output_data = json.loads(response.text)
    languages = json.loads(output_data["outputs"][0]["data"][0])

    return languages[1]


def prompt_lang_check(prompt, lang_type):
    """
    Checks if the given prompt matches the specified language and script criteria.

    Parameters:
    - user_lang (str): Language given by the user.
    - prompt (str): Text input to verify.
    - lang_type (int): Criteria type for language and script checking.

    Returns:
    - bool: True if criteria are met, False otherwise.
    """

    # get detected language and script from IndicLID

    detected_language, detected_script = get_lid(prompt)

    # Type 1 : Prompts in English

    if lang_type == 1:
        # Detected language must be english
        if detected_language != "eng":
            return False

    # Type 2 : Prompts in Indic Language and indic scripts
    elif lang_type == 2:
        # Detected language must match the user entered language
        if detected_language == "eng":
            return False

        # Detected script must be Indic script
        if detected_script == "Latn":
            return False

    # Type 3 : Prompts in Indic Language and latin script (transliterated)
    elif lang_type == 3:
        # Detected language must match the user entered language
        if detected_language == "eng":
            return False

        # Detected script must be Latin script
        if detected_script != "Latn":
            return False

    # Type 4 : Prompts must be english-indic code mixed in latin script
    elif lang_type == 4:
        # Detected language should be indic or english
        if detected_language == "other":
            return False

        # Detected script must be latin
        if detected_script != "Latn":
            return False

    return True


def evaluate_prompt_alignment(prompt, target_domain, target_intent):
    context = f"""
    On a scale of 1 to 5, how well does the statement '{prompt}' align with the intent of '{target_intent}' 
    and domain of '{target_domain}' (1 - highly unaligned, 5 - perfectly aligned)? 
    Be very lenient in checking. Output a json string with the keys- intent_score, domain_score, reason
    Output: """
    resp_dict = ast.literal_eval(get_response_for_domain_and_intent(context))

    intent = True if resp_dict["intent_score"] or target_intent is None >= 3 else False
    domain = True if resp_dict["domain_score"] or target_domain is None >= 3 else False

    return intent, domain, resp_dict["reason"]


def duplicate_check(ann_result, prompt):
    for r in ann_result:
        if r["prompt"] == prompt:
            return False
    return True
