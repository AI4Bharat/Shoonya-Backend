import uuid
import secrets
import string

## Define constants

# Indic Trans API supported languages
INDIC_TRANS_SUPPORTED_LANGUAGES = [
    "Assamese",
    "Bengali",
    "Gujarati",
    "Hindi",
    "Kannada",
    "Malayalam",
    "Marathi",
    "Odia",
    "Punjabi",
    "Tamil",
    "Telugu",
    "Bodo",
    "Maithili",
]

# List of languages supported by Azure Text Translation API
LANG_NAME_TO_CODE_AZURE = {
    "English": "en",
    "Assamese": "as",
    "Bengali": "bn",
    "Dhivehi": "dv",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",
    "Punjabi": "pa",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
}

# Language names to language codes
LANG_NAME_TO_CODE_GOOGLE = {
    "English": "en",
    "Assamese": "as",
    "Bhojpuri": "bho",
    "Bengali": "bn",
    "Bodo": "brx",
    "Dogri": "doi",
    "Dhivehi": "dv",
    "Konkani": "gom",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Kannada": "kn",
    "Kashmiri": "ks",
    "Mizo": "lus",
    "Maithili": "mai",
    "Malayalam": "ml",
    "Manipuri": "mni-Mtei",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Santali": "sat",
    "Sindhi": "sd",
    "Sinhala": "si",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
}

LANG_NAME_TO_CODE_ULCA = {
    "English": "en",
    "Assamese": "as",
    "Bhojpuri": "bho",
    "Bengali": "bn",
    "Bodo": "brx",
    "Dogri": "doi",
    "Dhivehi": "dv",
    "Konkani": "kok",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Kannada": "kn",
    "Kashmiri": "ks",
    "Mizo": "lus",
    "Maithili": "mai",
    "Malayalam": "ml",
    "Manipuri": "mni",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Santali": "sat",
    "Sindhi": "sd",
    "Sinhala": "si",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
}

LANG_NAME_TO_CODE_ITV2 = {
    "English": "en",
    "Assamese": "as",
    "Bhojpuri": "bho",
    "Bengali": "bn",
    "Bodo": "brx",
    "Dogri": "doi",
    "Dhivehi": "dv",
    "Konkani": "gom",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Kannada": "kn",
    "Kashmiri": "ks",
    "Mizo": "lus",
    "Maithili": "mai",
    "Malayalam": "ml",
    "Manipuri": "mni",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Santali": "sat",
    "Sindhi": "sd",
    "Sinhala": "si",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
}

# Language codes to language names
LANG_CODE_TO_NAME_GOOGLE = {
    lang_code: lang_name for lang_name, lang_code in LANG_NAME_TO_CODE_GOOGLE.items()
}

LANG_CODE_TO_NAME_ULCA = {
    lang_code: lang_name for lang_name, lang_code in LANG_NAME_TO_CODE_ULCA.items()
}

LANG_TRANS_MODEL_CODES = {
    "Hindi-English": 100,
    "Bengali-English": 101,
    "Tamil-English": 102,
    "English-Hindi": 103,
    "English-Tamil": 104,
    "English-Assamese": 110,
    "English-Bengali": 112,
    "English-Gujarati": 114,
    "English-Kannada": 116,
    "English-Malayalam": 118,
    "English-Marathi": 120,
    "English-Odia": 122,
    "English-Punjabi": 124,
    "English-Telugu": 126,
    "Assamese-English": 128,
    "Gujarati-English": 130,
    "Kannada-English": 132,
    "Malayalam-English": 134,
    "Marathi-English": 136,
    "Odia-English": 138,
    "Punjabi-English": 140,
    "Telugu-English": 142,
}  # 144 for all the other indic-indic translations

DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID = 144

TRANSLATOR_BATCH_SIZES = {
    "indic-trans": 75,
    "google": 128,
    "azure": 256,
}


def hash_upload(instance, filename):
    filename = str(uuid.uuid4())[0:8] + "-" + filename
    return "profile_photos/" + filename


def generate_random_string(length=12):
    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for i in range(length)
    )


def get_role_name(num):
    if num == 1:
        return "Annotator"
    elif num == 2:
        return "Reviewer"
    elif num == 3:
        return "Super Checker"
    elif num == 4:
        return "Workspace Manager"
    elif num == 5:
        return "Organization Owner"
    elif num == 6:
        return "Admin"
    else:
        return "Role Not Defined"
