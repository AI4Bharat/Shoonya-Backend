import requests
from dataset import models as dataset_models
from google.cloud import translate_v2 as translate
from rest_framework import status
from organizations.models import Organization
from users.models import User
from users.utils import (
    DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID,
    LANG_NAME_TO_CODE_GOOGLE,
    LANG_NAME_TO_CODE_ULCA,
    LANG_TRANS_MODEL_CODES,
)


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
        headers=headers,
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


def get_batch_translations(
    sentences_to_translate,
    source_lang,
    target_lang,
    api_type,
    checks_for_particular_languages,
):

    # Check the API type
    if api_type == "indic-trans":

        # Get the translation using the Indictrans NMT API
        translations_output = get_batch_translations_using_indictrans_nmt_api(
            sentence_list=sentences_to_translate,
            source_language=source_lang,
            target_language=target_lang,
            checks_for_particular_languages=checks_for_particular_languages,
        )

    elif api_type == "google":
        # Get the translation using the Indictrans NMT API
        translations_output = get_batch_translations_using_google_translate(
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
