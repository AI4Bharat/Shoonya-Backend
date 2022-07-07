import os
from tqdm import tqdm


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
