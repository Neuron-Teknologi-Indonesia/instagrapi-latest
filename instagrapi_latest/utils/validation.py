from instagrapi_latest.exceptions import ValidationError


def vassert(pred, message):
    if not pred:
        raise ValidationError(message)
