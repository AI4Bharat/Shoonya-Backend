import pandas as pd
import os
from dataset.models import TranslationPair, DatasetBase, DatasetInstance
import tqdm

df = pd.read_csv("SentenceText-2022-05-01.csv")
wiki = pd.read_csv("wiki-full-data.csv", names=["topic", "context", "sent"])

wiki_contexts = wiki["context"].tolist()
wiki_sents = wiki["sent"].tolist()

lang_dict = {
    "as": "Assamese",
    "bd": "Bodo",
    "bn": "Bengali",
    "dg": "Dogri",
    "gom": "Konkani",
    "gu": "Gujarati",
    "hi": "Hindi",
    "kn": "Kannada",
    "kha": "Khasi",
    "ks": "Kashmiri",
    "mai": "Maithili",
    "ml": "Malayalam",
    "mni": "Manipuri",
    "mr": "Marathi",
    "ne": "Nepali",
    "or": "Odia",
    "pa": "Punjabi",
    "sa": "Sanskrit",
    "sat": "Santhali",
    "sd": "Sindhi",
    "ta": "Tamil",
    "te": "Telugu",
    "ur": "Urdu",
}

id_dict = {
    "as": 26,
    "bd": 35,
    "bn": 28,
    "dg": 41,
    "gom": 43,
    "gu": 27,
    "hi": 29,
    "kn": 30,
    "kha": "Khasi",
    "ks": 42,
    "mai": 44,
    "ml": 31,
    "mni": 37,
    "mr": 32,
    "ne": 34,
    "or": 45,
    "pa": "Punjabi",
    "sa": 36,
    "sat": 46,
    "sd": "Sindhi",
    "ta": 33,
    "te": 25,
    "ur": 38,
}

# langs = ['as', 'bd', 'bn', 'gu', 'hi', 'kn', 'ml', 'mni', 'mr', 'sa', 'ne', 'ta', 'te', 'ur']
langs = ["dg", "or", "gom", "sat", "mai", "ks"]

for lang in langs:
    if lang == "bd" or lang == "sa" or lang == "mni":
        with open(f"all_data/hi.txt", "r") as f:
            lang_lines = f.readlines()
    elif lang == "dg" or lang == "mai" or lang == "sat":
        with open(f"all_data/hi.txt", "r") as f:
            lang_lines = f.readlines()
    elif lang == "ks":
        with open(f"all_data/ur.txt", "r") as f:
            lang_lines = f.readlines()
    elif lang == "gom":
        with open(f"all_data/mr.txt", "r") as f:
            lang_lines = f.readlines()
    else:
        with open(f"all_data/{lang}.txt", "r") as f:
            lang_lines = f.readlines()

    with open(f"all_data/en.txt", "r") as f:
        en_lines = f.readlines()
        en_lines = [x.strip() for x in en_lines]

    rows = []
    for i, row in tqdm.tqdm(df.iterrows()):
        dict_ = {}

        dict_["input_language"] = "English"
        dict_["input_text"] = row["text"]
        dict_["output_language"] = lang_dict[f"{lang}"]
        dict_["machine_translation"] = lang_lines[en_lines.index(row["text"])].strip()
        dict_["instance_id"] = id_dict[f"{lang}"]
        dict_["parent_data"] = row["id"]
        dict_["context"] = wiki_contexts[en_lines.index(row["text"])].strip()
        data_object = DatasetBase.objects.get(id=dict_["parent_data"])
        instance_object = DatasetInstance.objects.get(instance_id=dict_["instance_id"])
        t = TranslationPair(
            input_language=dict_["input_language"],
            input_text=dict_["input_text"],
            output_language=dict_["output_language"],
            machine_translation=dict_["machine_translation"],
            instance_id=instance_object,
            parent_data=data_object,
            context=dict_["context"],
        )
        t.save()
        # rows.append(dict_)

# df = pd.DataFrame(rows)

# os.mkdir(f'{lang}')
# for i in range(0, len(df), 2500):
#     df[i: i+2500].to_csv(f'{lang}/{lang}-translation-pairs-{i}.csv', index=False)
