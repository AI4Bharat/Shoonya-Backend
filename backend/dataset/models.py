"""
Model definitions for Dataset Management
"""
from django.db import models
from users.models import User, LANG_CHOICES
from organizations.models import Organization
from workspaces.models import Workspace


# List of all dataset types
DATASET_TYPE_CHOICES = [
    ("SentenceText", "SentenceText"),
    ("TranslationPair", "TranslationPair"),
    ("OCRDocument", "OCRDocument"),
    ("BlockText", "BlockText"),
]

GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("O", "Others"))

OCR_FILE_CHOICES = (("PDF", "pdf"), (("IMG", "image")))
OCR_TYPE_CHOICES = (("ST", "SceneText"), ("DT", "DenseText"))
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

# List of async functions pertaining to the dataset models
ALLOWED_CELERY_TASKS = [
    "dataset.tasks.upload_data_to_data_instance",
    "projects.tasks.export_project_new_record",
    "projects.tasks.export_project_in_place",
]


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
    organisation_id = models.ForeignKey(
        Organization, null=True, on_delete=models.SET_NULL
    )
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

    # class Meta:
    #     """Django definition of abstract model"""
    #     abstract = True


class SentenceText(DatasetBase):
    """
    Dataset for storing monolingual sentences.
    """

    language = models.CharField(
        verbose_name="language", choices=LANG_CHOICES, max_length=15
    )
    text = models.TextField(verbose_name="text", help_text=("Sentence Text"))
    context = models.TextField(
        verbose_name="context", help_text=("Context Text"), null=True, blank=True
    )
    corrected_text = models.TextField(
        verbose_name="corrected_text",
        help_text=("Corrected Sentence Text"),
        null=True,
        blank=True,
    )
    domain = models.CharField(
        verbose_name="domain",
        max_length=1024,
        help_text=("Domain of the Sentence"),
        null=True,
        blank=True,
    )
    quality_status = models.CharField(
        verbose_name="quality_status",
        default="Unchecked",
        max_length=32,
        choices=QUALITY_CHOICES,
        help_text=("Quality of the Sentence"),
    )

    def __str__(self):
        return str(self.id)


class TranslationPair(DatasetBase):
    """
    Dataset for storing translation pairs.
    """

    input_language = models.CharField(
        verbose_name="input_language", choices=LANG_CHOICES, max_length=15
    )
    output_language = models.CharField(
        verbose_name="output_language", choices=LANG_CHOICES, max_length=15
    )
    input_text = models.TextField(
        verbose_name="input_text", help_text=("The text to be translated")
    )
    output_text = models.TextField(
        verbose_name="output_text",
        null=True,
        blank=True,
        help_text=("The translation of the sentence"),
    )
    machine_translation = models.TextField(
        verbose_name="machine_translation",
        null=True,
        blank=True,
        help_text=("Machine translation of the sentence"),
    )
    context = models.TextField(
        verbose_name="context",
        null=True,
        blank=True,
        help_text=("Context of the sentence to be translated"),
    )
    labse_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=("Labse Score of the Translation"),
    )
    rating = models.IntegerField(
        verbose_name="translation_rating",
        null=True,
        blank=True,
        help_text=("Rating of the translation"),
    )

    def __str__(self):
        return str(self.id)


class OCRDocument(DatasetBase):
    """
    Dataset for storing OCR file urls and their annotations.
    """

    file_type = models.CharField(
        verbose_name="file_type", choices=OCR_FILE_CHOICES, max_length=3
    )
    file_url = models.URLField(
        verbose_name="bucket_url_for_file", max_length=500, null=True, blank=True
    )
    image_url = models.URLField(verbose_name="bucket_url_for_image", max_length=500)
    page_number = models.IntegerField(verbose_name="page_number", default=1)
    language = models.CharField(
        verbose_name="language", choices=LANG_CHOICES, max_length=15
    )
    ocr_type = models.CharField(
        verbose_name="ocr_type", choices=OCR_TYPE_CHOICES, max_length=3
    )
    ocr_domain = models.CharField(
        verbose_name="ocr_domain", choices=OCR_DOMAIN_CHOICES, max_length=3
    )
    # annotation_json = models.JSONField(
    #     verbose_name="annotation_json", null=True, blank=True
    # )

    annotation_bboxes = models.JSONField(
        verbose_name="annotation_bboxes", null=True, blank=True
    )

    annotation_transcripts = models.JSONField(
        verbose_name="annotation_transcripts", null=True, blank=True
    )

    annotation_labels = models.JSONField(
        verbose_name="annotation_labels", null=True, blank=True
    )

    prediction_json = models.JSONField(
        verbose_name="prediction_json", null=True, blank=True
    )

    def __str__(self):
        return str(self.id)


class BlockText(DatasetBase):
    """
    Dataset for storing monolingual data.
    """

    language = models.CharField(
        verbose_name="language", choices=LANG_CHOICES, max_length=15
    )
    text = models.TextField(
        verbose_name="text", help_text=("A block of text having many sentences")
    )
    splitted_text_prediction = models.JSONField(
        verbose_name="splitted_text_prediction",
        null=True,
        blank=True,
        help_text=("Prediction showing the block text split into sentences"),
    )
    splitted_text = models.TextField(
        verbose_name="splitted_text",
        null=True,
        blank=True,
        help_text=("Sentences Split from the Block Text"),
    )
    domain = models.CharField(
        verbose_name="domain", max_length=1024, help_text=("Domain of the block text")
    )

    def __str__(self):
        return str(self.id)


D1 = SentenceText
D10 = TranslationPair

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
