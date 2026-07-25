from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def process_image(image):
    img = Image.open(image)

    # Исправляем ориентацию по EXIF
    img = ImageOps.exif_transpose(img)

    # Приводим к RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Уменьшаем изображение с сохранением пропорций
    img.thumbnail(
        (
            settings.GALLERY_IMAGE_MAX_SIZE,
            settings.GALLERY_IMAGE_MAX_SIZE,
        ),
        Image.Resampling.LANCZOS,
    )

    output = BytesIO()

    save_kwargs = {
        "format": settings.GALLERY_IMAGE_FORMAT,
        "quality": settings.GALLERY_IMAGE_QUALITY,
        "optimize": True,
    }

    # Если НЕ хотим удалять метаданные — сохраняем EXIF
    if not settings.GALLERY_IMAGE_STRIP_METADATA:
        exif = img.info.get("exif")
        if exif:
            save_kwargs["exif"] = exif

    img.save(output, **save_kwargs)

    output.seek(0)

    filename = f"{Path(image.name).stem}.{settings.GALLERY_IMAGE_FORMAT.lower()}"

    return ContentFile(output.read(), name=filename)
