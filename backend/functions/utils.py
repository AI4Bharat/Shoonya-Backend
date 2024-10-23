import json
import os
import re

import requests
from dataset import models as dataset_models
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from rest_framework import status
from organizations.models import Organization
from users.models import User
from users.utils import (
    DEFAULT_ULCA_INDIC_TO_INDIC_MODEL_ID,
    LANG_NAME_TO_CODE_GOOGLE,
    LANG_NAME_TO_CODE_ULCA,
    LANG_TRANS_MODEL_CODES,
    LANG_NAME_TO_CODE_AZURE,
    LANG_NAME_TO_CODE_ITV2,
)
from google.cloud import vision
from users.utils import LANG_NAME_TO_CODE_ULCA

try:
    from utils.azure_translate import translator_object
except:
    pass


### Utility Functions
def check_if_particular_organization_owner(request):
    if request.user.role != User.ORGANIZATION_OWNER and not request.user.is_superuser:
        return {
            "error": "You are not an organization owner!",
            "status": status.HTTP_403_FORBIDDEN,
        }

    organization = Organization.objects.filter(
        pk=request.data["organization_id"]
    ).first()

    if not organization:
        return {"error": "Organization not found", "status": status.HTTP_404_NOT_FOUND}

    elif request.user.organization != organization:
        return {
            "error": "You are not the owner of this organization!",
            "status": status.HTTP_403_FORBIDDEN,
        }

    return {"status": status.HTTP_200_OK}
