import os
import numpy as np
import json
import ast
import openai
import requests
from pydantic import BaseModel, Field

from dataset.models import Interaction
from tasks.models import Annotation


def get_response_for_domain_and_intent(prompt):
    openai.api_type = os.getenv("LLM_INTERACTIONS_OPENAI_API_TYPE")
    openai.api_base = os.getenv("LLM_INTERACTIONS_OPENAI_API_BASE")
    openai.api_version = os.getenv("LLM_INTERACTIONS_OPENAI_API_VERSION")
    openai.api_key = os.getenv("LLM_INTERACTIONS_OPENAI_API_KEY")
    engine = "prompt-chat-gpt35"

    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        engine=engine,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=256,
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
    flag_lan, flag_scr = True, True
    temp_lang, temp_scr = "", ""
    # Type 1 : Prompts in English
    if lang_type == 1:
        # Detected language must be english
        if detected_language != "eng":
            flag_lan = False
        temp_lang = "English language"

    # Type 2 : Prompts in Indic Language and indic scripts
    elif lang_type == 2:
        # Detected language must match the user entered language
        if detected_language == "eng":
            flag_lan = False
        # Detected script must be Indic script
        if detected_script == "Latn":
            flag_scr = False
        temp_lang = "Indic language"
        temp_scr = "Indic script"

    # Type 3 : Prompts in Indic Language and latin script (transliterated)
    elif lang_type == 3:
        # Detected language must match the user entered language
        if detected_language == "eng":
            flag_lan = False
        # Detected script must be Latin script
        if detected_script != "Latn":
            flag_scr = False
        temp_lang = "Indic language"
        temp_scr = "Latin script"

    # Type 4 : Prompts must be english-indic code mixed in latin script
    elif lang_type == 4:
        # Detected language should be indic or english
        if detected_language == "other":
            flag_lan = False
        # Detected script must be latin
        if detected_script != "Latn":
            flag_scr = False
        temp_lang = "English-Indic mixed language"
        temp_scr = "Latin script"
    else:
        return False, "lang_type is inappropriate"

    if not flag_lan and not flag_scr:
        if len(temp_scr) == 0:
            return False, f"Prompts must be in {temp_lang}"
        return False, f"Prompts must be in {temp_lang} and {temp_scr}"
    elif not flag_lan:
        return False, f"Prompts must be in {temp_lang}"
    elif not flag_scr:
        return False, f"Prompts must be in {temp_scr}"
    return True


class Response(BaseModel):
    intent_score: float = Field(
        default=None, description="Score indicating alignment with the target intent"
    )
    domain_score: float = Field(
        default=None, description="Score indicating alignment with the target domain"
    )
    reason: str = Field(default=None, description="Explanation for the scores")


def evaluate_prompt_alignment(prompt, target_domain, target_intent):
    context = f"""
    On a scale of 1 to 5, how well does the statement '{prompt}' align with the intent of '{target_intent}' 
    and domain of '{target_domain}' (1 - highly unaligned, 5 - perfectly aligned)? 
    Be very lenient in checking. Output a json string with the keys- intent_score, domain_score, reason
    Output: """
    resp_dict = ast.literal_eval(get_response_for_domain_and_intent(context))
    response = Response(**resp_dict)
    intent_present = response.intent_score is not None
    domain_present = response.domain_score is not None

    if intent_present and domain_present:
        intent = response.intent_score >= 3
        domain = response.domain_score >= 3
        reason = response.reason
    elif not intent_present and not domain_present:
        intent = False
        domain = False
        reason = "Both intent_score and domain_score are not accessible from LLM"
    elif not intent_present:
        intent = False
        domain = response.domain_score >= 3
        reason = "Unable to fetch intent_score"
    else:  # domain not present
        intent = response.intent_score >= 3
        domain = False
        reason = "Unable to fetch domain_score"

    return intent, domain, reason


def duplicate_check(ann_result, prompt):
    for r in ann_result:
        if r["prompt"] == prompt:
            return False
    return True
