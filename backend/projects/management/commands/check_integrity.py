from django.core.management.base import BaseCommand, CommandError
from yaml import load
import traceback

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from dataset import models
from projects.registry_helper import ProjectRegistry


class Command(BaseCommand):
    """
    Command to check to do integrity checks before starting the server.
    """

    help = "Integrity checker command"

    def handle(self, *args, **kwargs):
        try:
            registry_helper = ProjectRegistry.get_instance()
            registry_helper.validate_registry()
            print("Integrity check sucessful")
        except:
            print(traceback.format_exc())
            raise CommandError("Initalization failed.")
