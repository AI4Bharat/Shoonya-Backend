"""
Model definitions for Dataset Management
"""

from django.db import models
from users.models import User

# List of all dataset types
DATASET_TYPE_CHOICES = [
    ("SentenceText", "SentenceText"),
    ("TranslationPair", "TranslationPair"),
]

# List of Indic languages
LANG_CHOICES = (
    ("bn", "Bengali"),
    ("gu", "Gujarati"),
    ("en", "English"),
    ("hi", "Hindi"),
    ("kn", "Kannada"),
    ("mr", "Marathi"),
    ("ne", "Nepali"),
    ("ne", "Odia"),
    ("pa", "Punjabi"),
    ("sa", "Sanskrit"),
    ("ta", "Tamil"),
    ("te", "Telugu"),
)

GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("O", "Others"))


class DatasetInstance(models.Model):
    """
    Dataset Instance Model
    """

    instance_id = models.IntegerField(
        verbose_name="dataset_instance_id", primary_key=True
    )

    parent_instance_id = models.IntegerField(
        verbose_name="parent_instance_id", blank=True, null=True, blank=True
    )
    instance_name = models.CharField(
        verbose_name="dataset_instance_name", max_length=1024
    )
    instance_description = models.TextField(
        verbose_name="dataset_instance_description", null=True, blank=True
    )
    organisation_id = models.IntegerField(verbose_name="organisation_id", null=True)
    workspace_id = models.IntegerField(verbose_name="workspace_id", null=True)
    dataset_type = models.CharField(
        verbose_name="dataset_type",
        choices=DATASET_TYPE_CHOICES,
        max_length=100,
    )
    users = models.ManyToManyField(User, related_name="dataset_users")

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

    data_id = models.AutoField(verbose_name="data_id", primary_key=True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    metadata_json = models.JSONField(
        verbose_name="metadata_json", null=True, blank=True
    )

    # class Meta:
    #     """Django definition of abstract model"""
    #     abstract = True


class SentenceText(DatasetBase):
    """
    Dataset for storing monolingual sentences.
    """

    lang_id = models.CharField(
        verbose_name="language_id", choices=LANG_CHOICES, max_length=3
    )
    text = models.TextField(verbose_name="text")
    domain = models.CharField(verbose_name="domain", max_length=1024)
    is_profane = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return str(self.data_id)


class TranslationPair(DatasetBase):
    """
    Dataset for storing translation pairs.
    """

    input_lang_id = models.CharField(
        verbose_name="input_language_id", choices=LANG_CHOICES, max_length=3
    )
    output_lang_id = models.CharField(
        verbose_name="output_language_id", choices=LANG_CHOICES, max_length=3
    )
    input_text = models.TextField(verbose_name="input_text")
    output_text = models.TextField(verbose_name="output_text", null=True, blank=True)
    machine_translation = models.TextField(
        verbose_name="machine_translation", null=True, blank=True
    )
    labse_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    rating = models.IntegerField(verbose_name="translation_rating", null=True, blank=True)

    def __str__(self):
        return str(self.data_id)


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
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

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
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

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
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

#     is_profane = models.BooleanField()
#     is_grammatically_correct = models.BooleanField
#     final_text = models.TextField()
#     perplexity = models.IntegerField()

# class Translation(models.Model):
#     """
#     Domain Type Translation Model
#     """
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

#     machine_translation = models.TextField()
#     human_tranlation = models.TextField()
#     labse_score = models.DecimalField(max_digits = 4, decimal_places = 2)
#     target_lang_id = models.CharField(verbose_name = 'target_language_id', choices = LANG_CHOICES, max_length=100)

# class OCR(models.Model):
#     """
#     Domain Type OCR Model
#     """
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

#     bboxes_json = models.JSONField()
#     is_clean = models.BooleanField()

# class Video(models.Model):
#     """
#     Domain Type Video Model
#     """
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

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
#     data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
#     instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
#     collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
#     bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
#     raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
#     metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
#     lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES, max_length=100)

#     sentence = models.TextField()
#     gloss_sequence = models.TextField()
#     duration = models.TimeField()
