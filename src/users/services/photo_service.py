# src/users/services/photo_service.py
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def process_image(image) -> ContentFile:
    """
    Обрабатывает загруженное изображение:
    - исправляет ориентацию по EXIF
    - конвертирует в RGB
    - уменьшает до GALLERY_IMAGE_MAX_SIZE по длинной стороне
    - сохраняет в GALLERY_IMAGE_FORMAT с качеством GALLERY_IMAGE_QUALITY
    - опционально очищает метаданные (GALLERY_IMAGE_STRIP_METADATA)
    """
    img = Image.open(image)

    # Исправляем ориентацию по EXIF (portrait vs landscape)
    img = ImageOps.exif_transpose(img)

    if img.mode != "RGB":
        img = img.convert("RGB")

    img.thumbnail(
        (settings.GALLERY_IMAGE_MAX_SIZE, settings.GALLERY_IMAGE_MAX_SIZE),
        Image.Resampling.LANCZOS,
    )

    output = BytesIO()
    save_kwargs = {
        "format": settings.GALLERY_IMAGE_FORMAT,
        "quality": settings.GALLERY_IMAGE_QUALITY,
        "optimize": True,
    }

    if not settings.GALLERY_IMAGE_STRIP_METADATA:
        exif = img.info.get("exif")
        if exif:
            save_kwargs["exif"] = exif

    img.save(output, **save_kwargs)
    output.seek(0)

    filename = f"{Path(image.name).stem}.{settings.GALLERY_IMAGE_FORMAT.lower()}"

    print(f"[PhotoService] Обработано: {image.name} → {filename} ({img.size[0]}x{img.size[1]})")

    return ContentFile(output.read(), name=filename)
