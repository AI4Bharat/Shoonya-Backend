import re
from typing import Tuple

from dateutil.parser import parse as date_parse


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

def no_of_words(string):
    """Return a the number of words in a given string

    Args:
        string (str): A string to count the number of words in 

    Returns:
        int: The number of words in a string. 
    """

    filter1 = [word for word in string.split() if len(word) > 1]
    filter2 = [word for word in filter1 if re.search('[a-zA-Z]', word) != None]
    return len(filter2) 
