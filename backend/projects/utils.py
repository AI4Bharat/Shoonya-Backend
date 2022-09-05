from typing import Tuple
from dateutil.parser import parse as date_parse
import re
import nltk

nltk.download("punkt")


def no_of_words(string):

    list_words = nltk.tokenize.word_tokenize(string)
    list_tokens = [word for word in list_words if len(word) > 1]
    length_of_sent = len(list_tokens)
    return length_of_sent


def is_valid_date(s: str) -> Tuple[bool, str]:
    try:
        d = date_parse(s)
    except ValueError:
        return (
            False,
            "Invalid Date Format",
        )

    if d.date() > d.today().date():
        return (False, "Please select dates upto Today")

    return (True, "")

def conversation_wordcount(conversations: list) -> int:
    """
    Returns the total word count of the Conversation DatasetInstance type
    """
    word_count = 0

    # Iterate through the list of dictionaries 
    for conversation in conversations:
        for sentence in conversation["sentences"]:
            word_count += no_of_words(sentence)
    return word_count