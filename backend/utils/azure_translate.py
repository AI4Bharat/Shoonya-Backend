import requests
from urllib.parse import urlencode
import traceback
import os


class AzureTranslator:
    def __init__(
        self,
        subscription_key: str,
        region: str,
        endpoint: str = "https://api.cognitive.microsofttranslator.com",
    ) -> None:
        self.http_headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "Ocp-Apim-Subscription-Region": region,
        }
        self.translate_endpoint = endpoint + "/translate?api-version=3.0&"
        self.languages_endpoint = endpoint + "/languages?api-version=3.0"

    def get_supported_languages(self) -> dict:
        return requests.get(self.languages_endpoint).json()["translation"]

    def batch_translate(self, texts: list, src_lang: str, tgt_lang: str) -> list:
        if not texts:
            return texts

        body = [{"text": text} for text in texts]
        query_string = urlencode(
            {
                "from": src_lang,
                "to": tgt_lang,
            }
        )

        try:
            response = requests.post(
                self.translate_endpoint + query_string,
                headers=self.http_headers,
                json=body,
            )
        except Exception:
            traceback.print_exc()
            return None

        try:
            response = response.json()
        except Exception:
            traceback.print_exc()
            print("Response:", response.text)
            return None

        return [payload["translations"][0]["text"] for payload in response]

    def text_translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        return self.batch_translate([text], src_lang, tgt_lang)[0]


# Create a translator instance
try:
    translator_object = AzureTranslator(
        os.environ["AZURE_TRANSLATOR_TEXT_SUBSCRIPTION_KEY"],
        os.environ["AZURE_TRANSLATOR_TEXT_REGION"],
        os.environ["AZURE_TRANSLATOR_TEXT_ENDPOINT"],
    )
except:
    pass
