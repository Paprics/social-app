# src/users/services/gallery.py
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from users.models.gallery import Photo, UserAlbum
from users.services.photo_service import process_image

DEFAULT_ALBUM_TITLE = "My Photos"
DEFAULT_ALBUM_SLUG = "my-photos"


def get_or_create_default_album(user) -> UserAlbum:
    """Возвращает дефолтный альбом пользователя, создаёт если не существует."""
    album, created = UserAlbum.objects.get_or_create(
        user=user,
        slug=DEFAULT_ALBUM_SLUG,
        defaults={
            "title": DEFAULT_ALBUM_TITLE,
            "album_type": UserAlbum.AlbumType.PHOTO,
            "visibility": UserAlbum.Visibility.PUBLIC,
            "is_visible": True,
        },
    )
    if created:
        print(f"[gallery] Создан дефолтный альбом для пользователя {user.pk}")
    return album


def get_remaining_slots(user) -> int:
    """Возвращает количество оставшихся слотов для загрузки фото."""
    used = Photo.objects.filter(album__user=user).count()
    return max(0, settings.GALLERY_MAX_PHOTOS - used)


def upload_photos(user, files: list) -> dict:
    """
    Пакетная загрузка фотографий в дефолтный альбом.

    Принимает список файлов, ограничивает по лимиту GALLERY_MAX_PHOTOS,
    обрабатывает каждый файл через process_image, сохраняет в БД.

    Возвращает dict с ключами:
        saved   — список сохранённых объектов Photo
        skipped — количество пропущенных (сверх лимита)
    """
    slots = get_remaining_slots(user)

    if slots == 0:
        print(f"[gallery] Пользователь {user.pk}: лимит исчерпан, загрузка отклонена")
        return {"saved": [], "skipped": len(files)}

    accepted = files[:slots]
    skipped_count = len(files) - len(accepted)

    if skipped_count > 0:
        print(
            f"[gallery] Пользователь {user.pk}: принято {len(accepted)}, пропущено {skipped_count} (лимит {settings.GALLERY_MAX_PHOTOS})"
        )

    album = get_or_create_default_album(user)
    saved = []

    for file in accepted:
        try:
            processed = process_image(file)
            photo = Photo(
                album=album,
                image=processed,
                title=file.name,
            )
            # Путь формируется через upload_to в модели
            photo.save()
            saved.append(photo)
            print(f"[gallery] Сохранено фото #{photo.pk} для пользователя {user.pk}")
        except Exception as exc:
            print(f"[gallery] Ошибка обработки файла {file.name}: {exc}")

    return {"saved": saved, "skipped": skipped_count}
