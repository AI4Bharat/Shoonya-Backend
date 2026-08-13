from django.apps import AppConfig


class DatasetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dataset"

    def ready(self):
        import dataset.signals  # noqa: F401