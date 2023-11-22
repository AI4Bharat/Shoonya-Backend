import json
import os
import re

import requests
from dataset import models as dataset_models
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from rest_framework import status
from organizations.models import Organization
from users.models import User
from users.utils import (
    DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID,
    LANG_NAME_TO_CODE_GOOGLE,
    LANG_NAME_TO_CODE_ULCA,
    LANG_TRANS_MODEL_CODES,
    LANG_NAME_TO_CODE_AZURE,
    LANG_NAME_TO_CODE_ITV2,
)
from google.cloud import vision
from users.utils import LANG_NAME_TO_CODE_ULCA

try:
    from utils.azure_translate import translator_object
except:
    pass


### Utility Functions
def check_if_particular_organization_owner(request):
    if request.user.role != User.ORGANIZATION_OWNER and not request.user.is_superuser:
        return {
            "error": "You are not an organization owner!",
            "status": status.HTTP_403_FORBIDDEN,
        }

    organization = Organization.objects.filter(
        pk=request.data["organization_id"]
    ).first()

    if not organization:
        return {"error": "Organization not found", "status": status.HTTP_404_NOT_FOUND}

    elif request.user.organization != organization:
        return {
            "error": "You are not the owner of this organization!",
            "status": status.HTTP_403_FORBIDDEN,
        }

    return {"status": status.HTTP_200_OK}


def check_conversation_translation_function_inputs(
    input_dataset_instance_id, output_dataset_instance_id
):
    """_summary_: Function to check the input parameters for the conversation translation function.
    This performs checks on input dataset instance and output dataset instance to see if their Conversation type or not.

    Returns:
        input_dataset_instance_id: ID of the input dataset which has to be a Conversation DatasetInstance.
        output_dataset_instance_id: ID of the output dataset which has to be a Conversation DatasetInstance.
    """

    # Check if the input and output dataset instances are Conversation DatasetInstance type
    try:
        input_or_output = "Input"
        input_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=input_dataset_instance_id
        )

        input_or_output = "Output"
        output_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=output_dataset_instance_id
        )

        if (
            input_dataset_instance.dataset_type != "Conversation"
            or output_dataset_instance.dataset_type != "Conversation"
        ):
            return {
                "message": "Input and output dataset instances should be of Conversation type",
                "status": status.HTTP_400_BAD_REQUEST,
            }

    except dataset_models.DatasetInstance.DoesNotExist:
        return {
            "message": f"{input_or_output} DatasetInstance does not exist!",
            "status": status.HTTP_404_NOT_FOUND,
        }

    return {"message": "Success!", "status": status.HTTP_200_OK}


def check_translation_function_inputs(
    input_dataset_instance_id, output_dataset_instance_id
):
    """Function to check the input parameters for the translation function.
    This performs checks on input dataset instance and output dataset instance.

    Returns:
        input_dataset_instance_id: ID of the input dataset which has to be a SentenceText DatasetInstance.
        output_dataset_instance_id: ID of the output dataset which has to be a TranslationPair DatasetInstance.
    """

    # Check if the input dataset instance is a SentenceText dataset
    try:
        input_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=input_dataset_instance_id
        )

        # Check if it is a sentence Text
        if input_dataset_instance.dataset_type != "SentenceText":
            return {
                "message": "Input dataset instance is not a SentenceText dataset.",
                "status": status.HTTP_400_BAD_REQUEST,
            }

    except dataset_models.DatasetInstance.DoesNotExist:
        return {
            "message": "Dataset instance does not exist!",
            "status": status.HTTP_404_NOT_FOUND,
        }

    # Check if the output dataset instance exists and is a TranslationPair type
    try:
        output_dataset_instance = dataset_models.DatasetInstance.objects.get(
            instance_id=output_dataset_instance_id
        )
        if output_dataset_instance.dataset_type != "TranslationPair":
            return {
                "message": "Output dataset instance is not of type TranslationPair",
                "status": status.HTTP_400_BAD_REQUEST,
            }

    except dataset_models.DatasetInstance.DoesNotExist:
        return {
            "message": "Output dataset instance does not exist! Create a TranslationPair DatasetInstance",
            "status": status.HTTP_404_NOT_FOUND,
        }

    return {"message": "Success", "status": status.HTTP_200_OK}


def get_batch_translations_using_indictrans_nmt_api(
    sentence_list,
    source_language,
    target_language,
    checks_for_particular_languages=False,
):
    """Function to get the translation for the input sentences using the IndicTrans NMT API.

    Args:
        sentence_list (str): List of sentences to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Final language of the sentence.
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.

    Returns:
        list: List of dictionaries containing the translated sentences.
    """

    # Get the translation model ID
    model_id = LANG_TRANS_MODEL_CODES.get(
        f"{source_language}-{target_language}", DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID
    )

    if checks_for_particular_languages:
        # Checks for particular languages
        if target_language in ["Bodo", "Maithili"]:
            target_language = "Hindi"
        elif target_language == "Kashmiri":
            target_language = "Urdu"

    # Convert language names to the language code
    source_language = LANG_NAME_TO_CODE_ULCA[source_language]
    target_language = LANG_NAME_TO_CODE_ULCA[target_language]

    # Create the input sentences list
    input_sentences = [{"source": sentence} for sentence in sentence_list]

    json_data = {
        "input": input_sentences,
        "config": {
            "modelId": model_id,
            "language": {
                "sourceLanguage": source_language,
                "targetLanguage": target_language,
            },
        },
    }

    try:
        response = requests.post(
            "https://nmt-models.ulcacontrib.org/aai4b-nmt-inference/v0/translate",
            json=json_data,
        )

        translations_output = response.json()["output"]

        # Collect the translated sentences
        return [translation["target"] for translation in translations_output]

    except Exception as e:
        return str(e)


def get_batch_translations_using_indictransv2_nmt_api(
    sentence_list,
    source_language,
    target_language,
    checks_for_particular_languages=False,
):
    """Function to get the translation for the input sentences using the IndicTrans V2 NMT API.

    Args:
        sentence_list (str): List of sentences to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Final language of the sentence.
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.

    Returns:
        list: List of dictionaries containing the translated sentences.
    """

    # Get the translation model ID
    model_id = LANG_TRANS_MODEL_CODES.get(
        f"{source_language}-{target_language}", DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID
    )

    if checks_for_particular_languages:
        # Checks for particular languages
        if target_language in ["Bodo", "Maithili"]:
            target_language = "Hindi"
        elif target_language == "Kashmiri":
            target_language = "Urdu"

    # Convert language names to the language code
    source_language = LANG_NAME_TO_CODE_ITV2[source_language]
    target_language = LANG_NAME_TO_CODE_ITV2[target_language]

    # Create the input sentences list
    input_sentences = [{"source": sentence} for sentence in sentence_list]

    json_data = {
        "input": input_sentences,
        "config": {
            "modelId": model_id,
            "language": {
                "sourceLanguage": source_language,
                "targetLanguage": target_language,
            },
        },
    }

    try:
        response = requests.post(
            "https://api.dhruva.ai4bharat.org/services/inference/translation?serviceId=ai4bharat/indictrans-v2-all-gpu--t4",
            json=json_data,
            headers={"authorization": os.getenv("INDIC_TRANS_V2_KEY")},
        )

        translations_output = response.json()["output"]

        # Collect the translated sentences
        return [translation["target"] for translation in translations_output]

    except Exception as e:
        return str(e)


def get_translation_using_cdac_model(input_sentence, source_language, target_language):
    """Function to get the translation for the input sentences using the CDAC model.

    Args:
        input_sentence (str): Sentence to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Final language of the sentence.

    Returns:
        str: Translated sentence.
    """

    # Get the translation model ID
    model_id = LANG_TRANS_MODEL_CODES.get(
        f"{source_language}-{target_language}", DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID
    )

    # Convert language names to the language code
    source_language = LANG_NAME_TO_CODE_ULCA[source_language]
    target_language = LANG_NAME_TO_CODE_ULCA[target_language]

    json_data = {
        "input": [
            {
                "source": input_sentence,
            },
        ],
        "config": {
            "modelId": model_id,
            "language": {
                "sourceLanguage": source_language,
                "targetLanguage": target_language,
            },
        },
    }

    response = requests.post(
        "https://cdac.ulcacontrib.org/aai4b-nmt-inference/v0/translate",
        json=json_data,
    )

    return response.json()["output"][0]["target"]


def get_batch_translations_using_google_translate(
    sentence_list,
    source_language,
    target_language,
    checks_for_particular_languages=False,
):
    """Function to get the translation for the input sentences using the Google Translate API.

    Args:
        sentence_list (str): List of sentences to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Final language of the sentence.
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.

    Returns:
        list: List of dictionaries containing the translated sentences.
    """

    if checks_for_particular_languages:
        # Checks for particular languages
        if target_language in ["Bodo", "Maithili"]:
            target_language = "Hindi"
        elif target_language == "Kashmiri":
            target_language = "Urdu"

    # Change the target language to the language code
    target_lang_code = LANG_NAME_TO_CODE_GOOGLE[target_language]
    source_lang_code = LANG_NAME_TO_CODE_GOOGLE[source_language]

    translate_client = translate.Client()

    try:
        translations_output = translate_client.translate(
            sentence_list,
            target_language=target_lang_code,
            source_language=source_lang_code,
        )

        # Return the translated sentences
        return [translation["translatedText"] for translation in translations_output]

    except Exception as e:
        return str(e)


def get_batch_translations_using_azure_translate(
    sentence_list,
    source_language,
    target_language,
    checks_for_particular_languages=False,
):
    """Function to get the translation for the input sentences using the Azure Translate API.

    Args:
        sentence_list (list): List of sentences to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Target language of the sentence.
        checks_for_particular_languages (bool, optional):  If True, checks for the particular languages in the translations. .Defaults to False.

    Returns:
        list/str: List of translated sentences or error message.
    """

    if checks_for_particular_languages:
        # Checks for particular languages
        if target_language in ["Bodo", "Maithili"]:
            target_language = "Hindi"
        elif target_language == "Kashmiri":
            target_language = "Urdu"

    # Change the target language to the language code
    target_lang_code = LANG_NAME_TO_CODE_AZURE[target_language]
    source_lang_code = LANG_NAME_TO_CODE_AZURE[source_language]

    try:
        return translator_object.batch_translate(
            sentence_list, source_lang_code, target_lang_code
        )
    except Exception as e:
        return str(e)


def get_batch_translations(
    sentences_to_translate,
    source_lang,
    target_lang,
    api_type,
    checks_for_particular_languages,
) -> dict:
    """Function to get the translation for the input sentences using various APIs.

    Args:
        sentences_to_translate (list): List of sentences to be translated.
        source_lang (str): Original language of the sentence.
        target_lang (str): Final language of the sentence.
        api_type (str): Type of API to be used for translation.
        checks_for_particular_languages (bool): If True, checks for the particular languages in the translations.

    Returns:
        dict: Dictionary containing the translated sentences or error message.
    """

    # Check the API type
    if api_type == "blank":
        # Return a list of empty sentences if api type is blank.
        return {"status": "success", "output": [""] * len(sentences_to_translate)}

    elif api_type == "indic-trans":
        # Get the translation using the Indictrans NMT API
        translations_output = get_batch_translations_using_indictrans_nmt_api(
            sentence_list=sentences_to_translate,
            source_language=source_lang,
            target_language=target_lang,
            checks_for_particular_languages=checks_for_particular_languages,
        )

    elif api_type == "indic-trans-v2":
        translations_output = get_batch_translations_using_indictransv2_nmt_api(
            sentence_list=sentences_to_translate,
            source_language=source_lang,
            target_language=target_lang,
            checks_for_particular_languages=checks_for_particular_languages,
        )

    elif api_type == "google":
        # Get the translation using the Google Translate API
        translations_output = get_batch_translations_using_google_translate(
            sentence_list=sentences_to_translate,
            source_language=source_lang,
            target_language=target_lang,
            checks_for_particular_languages=checks_for_particular_languages,
        )

    elif api_type == "azure":
        # Get the translation using the Azure Translate API
        translations_output = get_batch_translations_using_azure_translate(
            sentence_list=sentences_to_translate,
            source_language=source_lang,
            target_language=target_lang,
            checks_for_particular_languages=checks_for_particular_languages,
        )

    else:
        translations_output = "Invalid API type"

    # Check if the translations output is a string or a list
    if isinstance(translations_output, str):
        return {"status": "failure", "output": f"API Error: {translations_output}"}
    else:
        return {"status": "success", "output": translations_output}


def get_batch_ocr_predictions(id, image_url, api_type):
    """Function to get the ocr predictions for the images using various APIs.

    Args:
        id (int): id of the dataset instance
        image_url (str): Image whose text is to be predicted.
        api_type (str): Type of API to be used for translation.

    Returns:
        dict: Dictionary containing the predictions or error message.
    """
    # checking the API type
    if api_type == "google":
        ocr_predictions = get_batch_ocr_predictions_using_google(id, image_url)
    else:
        raise ValueError(f"{api_type} is an invalid API type")

    if ocr_predictions != "":
        return {"status": "Success", "output": ocr_predictions}
    else:
        return {"status": "Failure", "output": ocr_predictions}


# get ocr predictions from Google API.
def get_batch_ocr_predictions_using_google(id, image_url):
    # Creating a Google Cloud Vision client
    try:
        credentials = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "{}"))
        google_credentials = service_account.Credentials.from_service_account_info(
            credentials
        )
        client = vision.ImageAnnotatorClient(credentials=google_credentials)
    except Exception as p:
        raise Exception("Cannot connect to google cloud vision.")
    response = requests.get(image_url)
    if response.status_code != 200:
        print(
            f"Failed to download image for data instance with id-{id}. Status code: {response.status_code}"
        )
        return ""
    image = vision.Image(content=response.content)
    response = client.document_text_detection(image=image)
    ocr_predictions = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                paragraph_text = ""

                for word in paragraph.words:
                    word_text = "".join(symbol.text for symbol in word.symbols)
                    paragraph_text += word_text + " "

                paragraph_bounding_box = ocr_get_bounding_box(paragraph)
                ocr_prediction = {
                    "x": paragraph_bounding_box[0]["x"],
                    "y": paragraph_bounding_box[0]["y"],
                    "text": paragraph_text,
                    "width": paragraph_bounding_box[2]["x"]
                    - paragraph_bounding_box[0]["x"],
                    "height": paragraph_bounding_box[2]["y"]
                    - paragraph_bounding_box[0]["y"],
                    "labels": ["Body"],
                    "rotation": 0,
                    "original_width": page.width,
                    "original_height": page.height,
                }

                ocr_prediction = ocr_format_conversion(ocr_prediction)
                ocr_predictions.append(ocr_prediction)
    ocr_predictions_json = json.dumps(ocr_predictions, ensure_ascii=False)
    return ocr_predictions_json


# Function to get the bounding box for a feature
def ocr_get_bounding_box(feature):
    bounds = []
    for vertex in feature.bounding_box.vertices:
        bounds.append({"x": vertex.x, "y": vertex.y})
    return bounds


# Normalising the values obtained
def ocr_format_conversion(ocr_prediction):
    original_width, original_height = abs(ocr_prediction["original_width"]), abs(
        ocr_prediction["original_height"]
    )
    x = (abs(ocr_prediction["x"]) / original_width) * 100
    y = (abs(ocr_prediction["y"]) / original_height) * 100
    width = (abs(ocr_prediction["width"]) / original_width) * 100
    height = (abs(ocr_prediction["height"]) / original_height) * 100
    (
        ocr_prediction["x"],
        ocr_prediction["y"],
        ocr_prediction["width"],
        ocr_prediction["height"],
    ) = (x, y, width, height)
    return ocr_prediction


def get_batch_asr_predictions(id, audio_url, api_type, language):
    """Function to get the predictions for the input voice notes using various APIs.

    Args:
        id (int): id of the dataset instance
        audio_url (str): Image whose text is to be predicted.
        api_type (str): Type of API to be used for translation.

    Returns:
        dict: Dictionary containing predictions or error message.
    """
    # checking the API type
    if api_type == "dhruva_asr":
        asr_predictions = get_batch_asr_predictions_using_dhruva_asr(
            id, audio_url, language
        )
    else:
        raise ValueError(f"{api_type} is an invalid API type")

    if asr_predictions != "":
        return {"status": "Success", "output": asr_predictions}
    else:
        return {"status": "Failure", "output": asr_predictions}


def get_batch_asr_predictions_using_dhruva_asr(cur_id, audio_url, language):
    url = os.getenv("ASR_DHRUVA_URL")
    header = {"Authorization": os.getenv("ASR_DHRUVA_AUTHORIZATION")}
    if language == "Hindi":
        serviceId = "ai4bharat/conformer-hi-gpu--t4"
        languageCode = LANG_NAME_TO_CODE_ULCA[language]
    elif language == "English":
        serviceId = "ai4bharat/whisper-medium-en--gpu--t4"
        languageCode = LANG_NAME_TO_CODE_ULCA[language]
    elif language in [
        "Bengali",
        "Gujarati",
        "Marathi",
        "Odia",
        "Punjabi",
        "Sanskrit",
        "Urdu",
    ]:
        serviceId = "ai4bharat/conformer-multilingual-indo_aryan-gpu--t4"
        languageCode = LANG_NAME_TO_CODE_ULCA[language]
    elif language in ["Kannada", "Malayalam", "Tamil", "Telugu"]:
        serviceId = "ai4bharat/conformer-multilingual-dravidian-gpu--t4"
        languageCode = LANG_NAME_TO_CODE_ULCA[language]
    else:
        print(f"We don't support predictions for {language} language")
        return ""
    ds = {
        "config": {
            "serviceId": serviceId,
            "language": {"sourceLanguage": languageCode},
            "transcriptionFormat": {"value": "srt"},
        },
        "audio": [{"audioUri": f"{audio_url}"}],
    }
    try:
        response = requests.post(url, headers=header, json=ds, timeout=180)
        response_json = response.json()
        input_string = response_json["output"][0]["source"]
    except requests.exceptions.Timeout:
        print(f"The request took too long and timed out for id- {cur_id}.")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"An error occurred for id- {cur_id}: {e}")
        return ""
    start_time, end_time, texts = asr_extract_start_end_times_and_texts(
        "\n" + input_string
    )
    if (
        len(start_time) != len(end_time)
        or len(start_time) != len(texts)
        or len(end_time) != len(texts)
    ):
        print(f"Improper predictions for asr data item, id - {cur_id}")
        return ""
    prediction_json = []
    for i in range(len(start_time)):
        prediction_json_for_each_entry = {
            "speaker_id": 0,
            "start": start_time[i],
            "end": end_time[i],
            "text": texts[i],
        }
        prediction_json.append(prediction_json_for_each_entry)
    return prediction_json


# extracting data from the results obtained
def asr_extract_start_end_times_and_texts(input_str):
    input_list = input_str.split("\n")
    timestamps = []
    texts = []
    time_idx, text_idx = 2, 3
    while text_idx < len(input_list):
        timestamps.append(input_list[time_idx])
        time_idx += 4
        texts.append(input_list[text_idx])
        text_idx += 4
    start_time, end_time = asr_convert_start_end_times(timestamps)
    return start_time, end_time, texts


# converting starting and ending timings
def asr_convert_start_end_times(timestamps):
    formatted_start_times = []
    formatted_end_times = []
    for i in range(len(timestamps)):
        short_str = (
            re.split(r"[:,\s]", timestamps[i])[:4]
            + re.split(r"[:,\s]", timestamps[i])[5:]
        )
        h1, m1, s1, ms1, h2, m2, s2, ms2 = short_str

        # Calculate the start time in seconds with milliseconds
        start_time_seconds = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000.0

        # Calculate the end time in seconds with milliseconds
        end_time_seconds = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000.0

        formatted_start_times.append(f"{start_time_seconds:.3f}")
        formatted_end_times.append(f"{end_time_seconds:.3f}")
    return formatted_start_times, formatted_end_times
