import re
from typing import Tuple

from dateutil.parser import parse as date_parse
from django.db.models import Func


class Round(Func):
    function = "ROUND"
    template = "%(function)s(%(expressions)s::numeric, 2)"


def no_of_words(string):
    filter1 = [word for word in string.split() if len(word) > 1]
    filter2 = [word for word in filter1 if re.search('[a-zA-Z]', word) != None]
    length = len(filter2)
    return length 

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
