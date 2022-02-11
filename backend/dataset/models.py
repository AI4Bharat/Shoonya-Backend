from django.db import models
from shoonya_backend.mixins import DummyModelMixin

# Create your models here.


DOMAIN_CHOICES = [
    ('monolingual', 'Monolingual'),
    ('speechCollection', 'Speech Collection'),
    ('speechRecognition', 'Speech Recognition'),
    ('translation', 'Translation'),
    ('ocr', 'OCR'),
    ('video', 'Video'),
    ('videoChunk', 'Video Chunk'),
]

LANG_CHOICES = (
    ('hi','Hindi'),
    ('bn', 'Bengali'),
    ('pa','Punjabi'),
    ('te','Telugu'),
    ('ta','Tamil'),
)

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('Others', 'Others')
)

class DatasetInstance(models.Model):
    """
    Dataset Instance Model
    """
    instance_id = models.IntegerField(verbose_name = 'dataset_instance_id', primary_key = True)
    parent_instance_id = models.IntegerField(verbose_name = 'parent_instance_id', blank = True, null = True, blank = True)
    instance_name = models.CharField(verbose_name= 'dataset_instance_name', max_length = 1024)
    instance_description = models.TextField(verbose_name= 'dataset_instance_description')
    organisation_id = models.IntegerField(verbose_name = 'organisation_id' )
    workspace_id = models.IntegerField(verbose_name = 'workspace_id')
    domain_type = models.CharField(verbose_name= 'dataset_domain_type', choices = DOMAIN_CHOICES  , default  = 'monolingual')
##  users = models.ManyToManyField


class CollectionDataset(models.Model):
    """
    Collection Dataset Model
    """
    collection_id = models.IntegerField(verbose_name = 'collection_dataset_id', primary_key = True)
    collection_type = models.CharField(verbose_name= 'collection_domain_type', choices = DOMAIN_CHOICES  , default  = 'monolingual')
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    crawl_json = models.JSONField(verbose_name = 'collection_json')
    script_type = models.CharField(verbose_name = 'collection_script_type')
##  user_id = models.ForeignKey


class SpeechCollection(models.Model):
    """
    Domain Type Speech Collection Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    speaker_gender = models.CharField(verbose_name = 'speech_collection_speaker_gender', choices = GENDER_CHOICES, default = 'M')
    speaker_id = models.AutoField(verbose_name = 'speech_collection_speaker_id')
    audio_bucket_url = models.URLField(max_length = 400  , blank=False)
    voice_clarity = models.IntegerField(verbose_name = 'voice_clarity_of_sample')
    volume = models.IntegerField()
    noise = models.IntegerField()

    def __str__(self):
        return self.title + ', id=' + str(self.pk)

class SpeechRecognition(models.Model):
    """
    Domain Type Speech Recognition Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    speaker_gender = models.CharField(verbose_name = 'speech_recognition_speaker_gender', choices = GENDER_CHOICES  , default = 'M')
    speaker_id = models.AutoField(verbose_name = 'speech_recognition_speaker_id'  )
    voice_clarity = models.IntegerField(verbose_name = 'voice_clarity_of_sample' , blank=False)
    asr_transcript = models.TextField(verbose_name = 'automatic_speech_recognition_transcript') 
    human_transcipt = models.TextField(verbose_name = 'human_generated_transcript') 
    bg_music = models.BooleanField(verbose_name = 'background_music')

class Monolingual(models.Model):
    """
    Domain Type Monolingual Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    is_profane = models.BooleanField()
    is_grammatically_correct = models.BooleanField
    final_text = models.TextField()
    perplexity = models.IntegerField()

class Translation(models.Model):
    """
    Domain Type Translation Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    machine_translation = models.TextField()
    human_tranlation = models.TextField()
    labse_score = models.DecimalField(max_digits = 4, decimal_places = 2)
    target_lang_id = models.CharField(verbose_name = 'target_language_id', choices = LANG_CHOICES)

class OCR(models.Model):
    """
    Domain Type OCR Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    bboxes_json = models.JSONField()
    is_clean = models.BooleanField()

class Video(models.Model):
    """
    Domain Type Video Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    sentences = models.TextField()
    gloss_sequences = models.TextField()
    timestamps = models.TimeField()
    conversation_domain = models.CharField(max_length = 400)
    total_chunks = models.IntegerField(verbose_name = 'total_chunks_of_the_video')
    total_duration = models.TimeField()

class VideoChunk(models.Model):
    """
    Domain Type Video Chunk Model
    """
    data_id = models.IntegerField(verbose_name = 'dataitem_id', primary_key = True)
    instance_id = models.ForeignKey(DatasetInstance, on_delete=models.CASCADE)
    collection_id = models.ForeignKey(CollectionDataset, on_delete=models.CASCADE, null = True, blank = True)
    bucket_url = models.URLField(verbose_name = 'bucket_url_for_data', max_length = 400, null = True, blank = True)
    raw_data = models.TextField(verbose_name = 'raw_data', null = True, blank = True)
    metadata_json = models.JSONField(verbose_name = 'metadata_json' , null = True, blank = True)
    lang_id = models.CharField(verbose_name = 'language_id', choices = LANG_CHOICES)

    sentence = models.TextField()
    gloss_sequence = models.TextField()
    duration = models.TimeField()