# src/users/validators/image.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def validate_uploaded_image(file) -> None:
    """
    Выполняет полную проверку загруженного изображения.
    """

    _validate_file_is_not_empty(file)
    _validate_file_size(file)
    _validate_content_type(file)
    _validate_image(file)


def _validate_file_is_not_empty(file) -> None:
    if file.size == 0:
        raise ValidationError(_("The uploaded file is empty."))


def _validate_file_size(file) -> None:
    if file.size > settings.MAX_PHOTO_FILE_SIZE:
        raise ValidationError(_("The image exceeds the maximum allowed size."))


def _validate_content_type(file) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(_("Unsupported image format."))


def _validate_image(file) -> None:
    try:
        image = Image.open(file)
        image.verify()
    except Exception as exc:
        raise ValidationError(_("The uploaded file is not a valid image.")) from exc
    finally:
        file.seek(0)
