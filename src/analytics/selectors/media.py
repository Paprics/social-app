# src/analytics/selectors/media.py
"""Photo, album and storage analytics."""

import os

from django.conf import settings
from django.db.models import Count, Q

from analytics.dto.dashboard import Period, StatCard, StorageStats
from gallery.models import Photo, UserAlbum
from users.models.profile import Profile


def get_media_stats(period: Period) -> list[StatCard]:
    """Фото и альбомы — текущие и за период."""
    total_photos = Photo.objects.count()
    new_photos = Photo.objects.filter(created_at__range=(period.start, period.end)).count()
    prev_photos = Photo.objects.filter(
        created_at__range=(period.prev_start, period.prev_end)
    ).count()

    total_albums = UserAlbum.objects.filter(purpose="user").count()
    new_albums = UserAlbum.objects.filter(
        purpose="user", created_at__range=(period.start, period.end)
    ).count()
    prev_albums = UserAlbum.objects.filter(
        purpose="user", created_at__range=(period.prev_start, period.prev_end)
    ).count()

    users_with_avatar = Profile.objects.filter(
        user__is_active=True, avatar_photo__isnull=False
    ).count()
    users_total = Profile.objects.filter(user__is_active=True).count() or 1

    users_no_photo = (
        Profile.objects.filter(user__is_active=True)
        .annotate(photo_count=Count("user__galleries__photos"))
        .filter(photo_count=0)
        .count()
    )

    return [
        StatCard("Total photos", total_photos, total_photos - new_photos),
        StatCard("New photos", new_photos, prev_photos),
        StatCard("Total albums", total_albums, total_albums - new_albums),
        StatCard("New albums", new_albums, prev_albums),
        StatCard("With avatar", users_with_avatar, 0,
                 unit=f"{round(users_with_avatar/users_total*100,1)}%"),
        StatCard("No photos", users_no_photo, 0,
                 unit=f"{round(users_no_photo/users_total*100,1)}%"),
    ]


def get_storage_stats() -> StorageStats:
    """Физический размер медиа-файлов на диске."""
    media_root = settings.MEDIA_ROOT
    total_bytes = 0
    media_bytes = 0
    avatars_bytes = 0
    files_count = 0

    if not os.path.isdir(media_root):
        return StorageStats(0, 0, 0, 0)

    photos_dir = os.path.join(media_root, "photos")
    messenger_dir = os.path.join(media_root, "messenger")

    # Весь MEDIA_ROOT
    for dirpath, _, filenames in os.walk(media_root):
        for fn in filenames:
            try:
                size = os.path.getsize(os.path.join(dirpath, fn))
                total_bytes += size
                files_count += 1
            except OSError:
                pass

    # Только photos/
    if os.path.isdir(photos_dir):
        for dirpath, _, filenames in os.walk(photos_dir):
            for fn in filenames:
                try:
                    media_bytes += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    pass

    # Аватары — profile_photos albums
    from gallery.models import UserAlbum as _UA
    avatar_album_ids = list(
        _UA.objects.filter(purpose="profile_photos").values_list("id", flat=True)
    )
    avatar_paths = list(
        Photo.objects.filter(album_id__in=avatar_album_ids).values_list("image", flat=True)
    )
    for rel_path in avatar_paths:
        full = os.path.join(media_root, str(rel_path))
        try:
            avatars_bytes += os.path.getsize(full)
        except OSError:
            pass

    return StorageStats(
        total_bytes=total_bytes,
        media_bytes=media_bytes,
        avatars_bytes=avatars_bytes,
        files_count=files_count,
    )
