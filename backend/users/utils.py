import uuid


def hash_upload(instance, filename):
    filename = str(uuid.uuid4())[0:8] + "-" + filename
    return "profile_photos/" + filename
