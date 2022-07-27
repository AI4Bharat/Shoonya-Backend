import uuid

## Define constants 

# Language names to code 
LANG_NAME_TO_CODE = {
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
    "Urdu": "ur"
}

# Language code to language name 
LANG_CODE_TO_NAME = {
    "en": "English",
    "as": "Assamese",
    "bho": "Bhojpuri",
    "bn": "Bengali",
    "brx": "Bodo",
    "doi": "Dogri",
    "dv": "Dhivehi",
    "gom": "Konkani",
    "gu": "Gujarati",
    "hi": "Hindi",
    "kn": "Kannada",
    "ks": "Kashmiri",
    "lus": "Mizo",
    "mai": "Maithili",
    "ml": "Malayalam",
    "mni": "Manipuri",
    "mni-Mtei": "Manipuri",
    "mr": "Marathi",
    "ne": "Nepali",
    "or": "Odia",
    "pa": "Punjabi",
    "sa": "Sanskrit",
    "sat": "Santali",
    "sd": "Sindhi",
    "si": "Sinhala",
    "ta": "Tamil",
    "te": "Telugu",
    "ur": "Urdu"
}

def hash_upload(instance, filename):
    filename = str(uuid.uuid4())[0:8] + "-" + filename
    return "profile_photos/" + filename
