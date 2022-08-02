import requests
import os
from tqdm import tqdm
from users.utils import LANG_NAME_TO_CODE_ULCA, LANG_TRANS_MODEL_CODES

### Utility Functions 
def get_batch_translations_using_indictrans_nmt_api(sentence_list, source_language, target_language): 

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

        output = ast.literal_eval(response.content.decode("utf-8"))
        return output['output']

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


# class GoogleTranslator:
#     """Class to handle Google Translations for different dataset instance types"""

#     def __init__(self):

#         if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
#             print("Set $GOOGLE_APPLICATION_CREDENTIALS to use Google Translate API")

#         # from google.cloud import translate as gtranslate
#         from google.cloud import translate_v2 as translate

#         self.client = translate.Client()

#     def batch_translate(
#         self, sentences: list, input_lang: str, output_lang: str, batch_size: int = 100
#     ):
#         """_summary_: Function to translate a batch of input sentences into the target language

#         Args:
#             sentences (list): List of sentences to be translated
#             input_lang (str): Language of the input sentences
#             output_lang (str): Language of the output sentences
#             batch_size (int, optional): Batch size to perform the translations in. Defaults to 100.

#         Returns:
#             _type_: _description_
#         """
#         translations = []
#         pbar = tqdm(total=len(sentences), position=0, leave=True)
#         i = 0
#         while i < len(sentences):
#             response = self.client.translate(
#                 values=sentences[i : i + batch_size],
#                 source_language=input_lang,
#                 target_language=output_lang,
#             )

#             translations.extend(
#                 translation["translatedText"] for translation in response
#             )
#             pbar.update(len(response))
#             i += batch_size

#         pbar.close()
#         return translations
