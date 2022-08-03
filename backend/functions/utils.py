import requests
from google.cloud import translate_v2 as translate
from users.utils import (
        LANG_NAME_TO_CODE_GOOGLE, 
        LANG_NAME_TO_CODE_ULCA,
        LANG_TRANS_MODEL_CODES
    )


### Utility Functions
def check_translation_function_inputs(): 
    pass 

def get_batch_translations_using_indictrans_nmt_api(
    sentence_list, source_language, target_language
):

    """Function to get the translation for the input sentences using the IndicTrans NMT API.

    Args:
        input_sentence (str): Sentence to be translated.
        source_language (str): Original language of the sentence.
        target_language (str): Final language of the sentence.

    Returns:
        list: List of dictionaries containing the translated sentences. 
    """

    # Get the translation model ID
    model_id = LANG_TRANS_MODEL_CODES.get(f"{source_language}-{target_language}", 144)

    # Convert language names to the language code
    source_language = LANG_NAME_TO_CODE_ULCA[source_language]
    target_language = LANG_NAME_TO_CODE_ULCA[target_language]

    # Create the input sentences list
    input_sentences = [{"source": sentence} for sentence in sentence_list]

    headers = {
        # Already added when you pass json= but not when you pass data=
        # 'Content-Type': 'application/json',
    }

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
            headers=headers,
            json=json_data,
        )

        return response.json()["output"]

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
    model_id = LANG_TRANS_MODEL_CODES.get(f"{source_language}-{target_language}", 144)

    # Convert language names to the language code
    source_language = LANG_NAME_TO_CODE_ULCA[source_language]
    target_language = LANG_NAME_TO_CODE_ULCA[target_language]

    headers = {
        # Already added when you pass json= but not when you pass data=
        # 'Content-Type': 'application/json',
    }

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

def get_batch_translations_using_google_translate(sentence_list, target_language): 

    # Change the target language to the language code
    target_lang_code = LANG_NAME_TO_CODE_GOOGLE[target_language]

    translate_client = translate.Client()

    try: 
        return translate_client.translate(sentence_list, target_language=target_lang_code)

    except Exception as e:
        return str(e)

