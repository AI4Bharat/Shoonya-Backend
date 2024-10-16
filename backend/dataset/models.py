"""
Model definitions for Dataset Management
"""
from django.db import models
from users.models import User, LANG_CHOICES
from organizations.models import Organization
from workspaces.models import Workspace


# List of all dataset types
DATASET_TYPE_CHOICES = [
    ("PromptBase", "PromptBase"),
    ("PromptAnswer", "PromptAnswer"),
    ("PromptAnswerEvaluation", "PromptAnswerEvaluation"),
    ("Interaction", "Interaction"),
    ("Instruction", "Instruction"),
    ("MultiModelInteraction", "MultiModelInteraction"),
]

GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("O", "Others"))

OCR_FILE_CHOICES = (
    ("PDF", "pdf"),
    ("JPG", "JPG_image"),
    ("JPEG", "JPEG_image"),
    ("PNG", "PNG_image"),
)
OCR_TYPE_CHOICES = (
    ("ST", "ScenicText"),
    ("DT", "DenseText"),
    ("PR", "Printed"),
    ("HN", "Handwritten"),
)
OCR_DOMAIN_CHOICES = (
    ("BO", "Books"),
    ("FO", "Forms"),
    ("OT", "Others"),
)

QUALITY_CHOICES = (
    ("Unchecked", "Unchecked"),
    ("Clean", "Clean"),
    ("Profane", "Profane"),
    ("Difficult vocabulary", "Difficult vocabulary"),
    ("Ambiguous sentence", "Ambiguous sentence"),
    ("Context incomplete", "Context incomplete"),
    ("Corrupt", "Corrupt"),
)

SENTENCE_TEXT_DOMAIN_CHOICES = (
    ("None", "None"),
    ("Business", "Business"),
    ("Culture", "Culture"),
    ("General", "General"),
    ("News", "News"),
    ("Education", "Education"),
    ("Legal", "Legal"),
    ("Government-Press-Release", "Government-Press-Release"),
    ("Healthcare", "Healthcare"),
    ("Agriculture", "Agriculture"),
    ("Automobile", "Automobile"),
    ("Tourism", "Tourism"),
    ("Financial", "Financial"),
    ("Movies", "Movies"),
    ("Subtitles", "Subtitles"),
    ("Sports", "Sports"),
    ("Technology", "Technology"),
    ("Lifestyle", "Lifestyle"),
    ("Entertainment", "Entertainment"),
    ("Parliamentary", "Parliamentary"),
    ("Art-and-Culture", "Art-and-Culture"),
    ("Economy", "Economy"),
    ("History", "History"),
    ("Philosophy", "Philosophy"),
    ("Religion", "Religion"),
    ("National-Security-and-Defence", "National-Security-and-Defence"),
    ("Literature", "Literature"),
    ("Geography", "Geography"),
)

# List of async functions pertaining to the dataset models
ALLOWED_CELERY_TASKS = [
    "dataset.tasks.upload_data_to_data_instance",
    "projects.tasks.export_project_new_record",
    "projects.tasks.export_project_in_place",
]

LANGUAGE_CHOICES = [
    ("English", "English"),
    ("Assamese", "Assamese"),
    ("Bengali", "Bengali"),
    ("Bodo", "Bodo"),
    ("Dogri", "Dogri"),
    ("Gujarati", "Gujarati"),
    ("Hindi", "Hindi"),
    ("Kannada", "Kannada"),
    ("Kashmiri", "Kashmiri"),
    ("Konkani", "Konkani"),
    ("Maithili", "Maithili"),
    ("Malayalam", "Malayalam"),
    ("Manipuri", "Manipuri"),
    ("Marathi", "Marathi"),
    ("Nepali", "Nepali"),
    ("Odia", "Odia"),
    ("Punjabi", "Punjabi"),
    ("Sanskrit", "Sanskrit"),
    ("Santali", "Santali"),
    ("Sindhi", "Sindhi"),
    ("Sinhala", "Sinhala"),
    ("Tamil", "Tamil"),
    ("Telugu", "Telugu"),
    ("Urdu", "Urdu"),
]

LANGUAGE_CHOICES_INSTRUCTIONS = (
    ("1", "English(Any script)"),
    ("2", "Indic(Indic script)"),
    ("3", "Indic(Latin script)"),
    ("4", "Indic/English(Latin script)"),
)

GPT35 = "GPT3.5"
GPT4 = "GPT4"
LLAMA2 = "LLAMA2"
GPT4OMini = "GPT4OMini"
GPT4O = "GPT4O"
GEMMA = "GEMMA"

LLM_CHOICES = (
    (GPT35, GPT35),
    (GPT4, GPT4),
    (LLAMA2, LLAMA2),
    (GPT4OMini, GPT4OMini),
    (GPT4O, GPT4O),
    (GEMMA, GEMMA),
)


class DatasetInstance(models.Model):
    """
    Dataset Instance Model
    """

    instance_id = models.AutoField(verbose_name="dataset_instance_id", primary_key=True)

    parent_instance_id = models.IntegerField(
        verbose_name="parent_instance_id",
        blank=True,
        null=True,
        help_text=("The instance id of the source dataset"),
    )
    instance_name = models.CharField(
        verbose_name="dataset_instance_name", max_length=1024
    )
    instance_description = models.TextField(
        verbose_name="dataset_instance_description", null=True, blank=True
    )
    organisation_id = models.ForeignKey(Organization, on_delete=models.CASCADE)
    dataset_type = models.CharField(
        verbose_name="dataset_type",
        choices=DATASET_TYPE_CHOICES,
        max_length=100,
        help_text=("Dataset Type which is specific for each annotation task"),
    )
    users = models.ManyToManyField(User, related_name="dataset_users")
    public_to_managers = models.BooleanField(
        verbose_name="dataset_public_to_managers", default=False
    )

    class Meta:
        db_table = "dataset_instance"
        indexes = [
            models.Index(fields=["instance_id"]),
        ]

    def __str__(self):
        return str(self.instance_name)


class DatasetBase(models.Model):
    """
    Abstract class for all datasets

    All dataset types should inherit this model.
    The model stores fields common to all datasets.
    """

    # id = models.AutoField(verbose_name="id", primary_key=True)
    parent_data = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    metadata_json = models.JSONField(
        verbose_name="metadata_json",
        null=True,
        blank=True,
        help_text=(
            "Metadata having details related to the annotation tasks or functions this data was involved in"
        ),
    )
    draft_data_json = models.JSONField(
        verbose_name="draft_data_json",
        null=True,
        blank=True,
        help_text=(
            "Json data having annotation field  information and data regarding externally annotated data"
        ),
    )

    # class Meta:
    #     """Django definition of abstract model"""
    #     abstract = True


# class CollectionDataset(models.Model):
#     """
#     Collection Dataset Model
#     """
#     collection_id = models.IntegerField(verbose_name = 'collection_dataset_id', primary_key = True)
#     collection_type = models.CharField(verbose_name= 'collection_domain_type', max_length = 100, choices = DOMAIN_CHOICES  , default  = 'monolingual')
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     crawl_json = models.JSONField(verbose_name = 'collection_json')
#     script_type = models.CharField(verbose_name = 'collection_script_type', max_length = 100,)
#     user_id = models.ForeignKey(User, on_delete = models.CASCADE, default = 1)


# class SpeechCollection(models.Model):
#     """
#     Domain Type Speech Collection Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     speaker_gender = models.CharField(verbose_name = 'speech_collection_speaker_gender', choices = GENDER_CHOICES, default = 'M', max_length=100)
#     speaker_id = models.IntegerField(verbose_name = 'speech_collection_speaker_id')
#     audio_bucket_url = models.URLField(max_length = 400  , blank=False)
#     voice_clarity = models.IntegerField(verbose_name = 'voice_clarity_of_sample')
#     volume = models.IntegerField()
#     noise = models.IntegerField()

#     def __str__(self):
#         return self.title + ', id=' + str(self.pk)

# class SpeechRecognition(models.Model):
#     """
#     Domain Type Speech Recognition Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     speaker_gender = models.CharField(verbose_name = 'speech_recognition_speaker_gender', choices = GENDER_CHOICES  , default = 'M', max_length=100)
#     speaker_id = models.IntegerField(verbose_name = 'speech_recognition_speaker_id'  )
#     voice_clarity = models.IntegerField(verbose_name = 'voice_clarity_of_sample' , blank=False)
#     asr_transcript = models.TextField(verbose_name = 'automatic_speech_recognition_transcript')
#     human_transcipt = models.TextField(verbose_name = 'human_generated_transcript')
#     bg_music = models.BooleanField(verbose_name = 'background_music')

# class Monolingual(models.Model):
#     """
#     Domain Type Monolingual Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     is_Profane = models.BooleanField()
#     is_grammatically_correct = models.BooleanField
#     final_text = models.TextField()
#     perplexity = models.IntegerField()

# class Translation(models.Model):
#     """
#     Domain Type Translation Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     machine_translation = models.TextField()
#     human_tranlation = models.TextField()
#     labse_score = models.DecimalField(max_digits = 4, decimal_places = 2)
#     target_language = models.CharField(verbose_name = 'target_language', choices = LANG_CHOICES, max_length=100)

# class OCR(models.Model):
#     """
#     Domain Type OCR Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     bboxes_json = models.JSONField()
#     is_clean = models.BooleanField()

# class Video(models.Model):
#     """
#     Domain Type Video Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     sentences = models.TextField()
#     gloss_sequences = models.TextField()
#     timestamps = models.TimeField()
#     conversation_domain = models.CharField(max_length = 400)
#     total_chunks = models.IntegerField(verbose_name = 'total_chunks_of_the_video')
#     total_duration = models.TimeField()

# class VideoChunk(models.Model):
#     """
#     Domain Type Video Chunk Model
#     """
#     id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     language = models.CharField(verbose_name = 'language', choices = LANG_CHOICES, max_length=100)

#     sentence = models.TextField()
#     gloss_sequence = models.TextField()
#     duration = models.TimeField()


class Instruction(DatasetBase):
    """
    Subclass model for Instructions
    """

    meta_info_model = models.CharField(
        max_length=255,
        verbose_name="Meta Info Model",
        default="GPT3.5",
        choices=LLM_CHOICES,
        help_text="Model information for the instruction",
    )
    meta_info_auto_generated = models.BooleanField(
        verbose_name="Meta Info Auto Generated",
        null=True,
        blank=True,
        help_text="Whether the instruction has been auto-generated",
    )
    meta_info_intent = models.CharField(
        max_length=255,
        verbose_name="Meta Info Intent",
        help_text="Intent information for the instruction",
    )
    meta_info_domain = models.CharField(
        max_length=255,
        verbose_name="Meta Info Domain",
        help_text="Domain information for the instruction",
    )
    meta_info_structure = models.CharField(
        max_length=255,
        verbose_name="Meta Info Structure",
        null=True,
        blank=True,
        help_text="Structure information for the instruction",
    )
    meta_info_language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES_INSTRUCTIONS,
        verbose_name="Meta Info Language",
        help_text="Language of the instruction",
    )
    instruction_data = models.TextField(verbose_name="Instruction_data")
    examples = models.TextField(verbose_name="Examples")
    hint = models.TextField(verbose_name="Hint")

    def __str__(self):
        return f"{self.id} - {self.instruction_data}"


class Interaction(DatasetBase):
    """
    Subclass model for Interactions
    """

    instruction_id = models.ForeignKey(
        Instruction,
        on_delete=models.CASCADE,
        verbose_name="Instruction ID",
        help_text="ID of the related instruction",
        null=True,
        blank=True,
    )
    interactions_json = models.JSONField(verbose_name="Interactions JSON")
    no_of_turns = models.IntegerField(
        verbose_name="Number of Turns",
        help_text="Number of turns in the interaction",
        null=True,
        blank=True,
    )
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        verbose_name="Language",
        help_text="Language of the interaction",
    )
    model = models.CharField(
        max_length=255, verbose_name="Model", help_text="Model used for the interaction"
    )
    datetime = models.DateTimeField(
        verbose_name="Datetime",
        help_text="Timestamp of the interaction",
        null=True,
        blank=True,
    )
    time_taken = models.FloatField(
        verbose_name="Time Taken", help_text="Time taken for the interaction"
    )

    def __str__(self):
        return f"{self.id} - Interaction with Instruction {self.instruction_id_id}"


class PromptBase(DatasetBase):
    """
    Dataset for storing prompt data
    """

    prompt = models.TextField(
        verbose_name="prompt",
        null=True,
        blank=True,
        help_text=("Prompt of the conversation"),
    )
    instruction_id = models.ForeignKey(
        Instruction, on_delete=models.CASCADE, null=True, blank=True
    )
    language = models.CharField(
        verbose_name="language", choices=LANG_CHOICES, max_length=15
    )

    def __str__(self):
        return str(self.id)


class PromptAnswer(DatasetBase):
    """
    Dataset for storing prompt response data
    """

    interaction_id = models.ForeignKey(
        Interaction, on_delete=models.CASCADE, null=True, blank=True
    )
    prompt = models.TextField(
        verbose_name="prompt",
        null=True,
        blank=True,
        help_text=("Prompt of the conversation"),
    )
    output = models.TextField(
        verbose_name="response",
        null=True,
        blank=True,
        help_text=("Response of the conversation"),
    )
    model = models.CharField(
        verbose_name="model",
        max_length=16,
        help_text=("Model of the response"),
        choices=LLM_CHOICES,
    )
    language = models.CharField(
        verbose_name="language", choices=LANG_CHOICES, max_length=15
    )
    eval_form_output_json = models.JSONField(
        verbose_name="evaluation_form_output",
        null=True,
        blank=True,
        help_text=("Form output of the prompt response (JSON)"),
    )
    eval_time_taken = models.FloatField(
        verbose_name="evaluation_time_taken",
        null=True,
        blank=True,
        help_text=("Time taken to complete the prompt response"),
    )
    prompt_output_pair_id = models.CharField(
        verbose_name="prompt_output_pair_id",
        max_length=16,
        help_text=("prompt_output_pair_id"),
        null=True,
    )

    def __str__(self):
        return str(self.id)


class PromptAnswerEvaluation(DatasetBase):
    """
    Dataset for storing prompt response evaluation data
    """

    model_output_id = models.ForeignKey(
        PromptAnswer, on_delete=models.CASCADE, null=True, blank=True
    )
    output_likert_score = models.IntegerField(
        verbose_name="prompt_response_rating",
        null=True,
        blank=True,
        help_text=("Rating of the prompt response"),
    )
    form_output_json = models.JSONField(
        verbose_name="form_output",
        null=True,
        blank=True,
        help_text=("Form output of the prompt response (JSON)"),
    )
    datetime = models.DateTimeField(
        verbose_name="datetime",
        null=True,
        blank=True,
        help_text=("Date and time of the prompt response"),
    )
    time_taken = models.FloatField(
        verbose_name="time_taken",
        null=True,
        blank=True,
        help_text=("Time taken to complete the prompt response"),
    )

    def __str__(self):
        return str(self.id)


class MultiModelInteraction(DatasetBase):
    """
    Subclass model for MultiModelInteraction
    """

    parent_interaction_ids = models.JSONField(
        verbose_name="Parent Interaction Ids",
        help_text="A json containing all the parent ids",
        null=True,
        blank=True,
    )
    multiple_interaction_json = models.JSONField(
        verbose_name="Multiple Interaction Json",
        help_text="A json containing interactions for a single prompt from multiple models.",
    )
    eval_form_json = models.JSONField(
        verbose_name="form_output",
        null=True,
        blank=True,
        help_text="Form output for all the interactions",
    )
    no_of_turns = models.IntegerField(
        verbose_name="Number of Turns",
        help_text="Number of turns in the interaction",
        null=True,
        blank=True,
    )
    no_of_models = models.IntegerField(
        verbose_name="Number of Models",
        help_text="Number of models in the interaction",
        null=True,
        blank=True,
    )
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        verbose_name="Language",
        help_text="Language of the interaction",
    )
    datetime = models.DateTimeField(
        verbose_name="Datetime",
        help_text="Timestamp of the interaction",
        null=True,
        blank=True,
    )
