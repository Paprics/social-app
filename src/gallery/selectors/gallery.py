# src/gallery/selectors/gallery.py

from django.conf import settings
from django.contrib.auth import get_user_model

from gallery.models import Photo, UserAlbum
from gallery.services.access import GalleryAccessService
from gallery.services.gallery import get_remaining_slots
from users.services.access import ProfileAccessService
from users.services.friendship_service import FriendshipService

User = get_user_model()


def get_gallery_target_user(*, user_id):
    """
    Return gallery owner with relations required by gallery pages.
    """

    return (
        User.objects.select_related(
            "profile",
            "settings",
        )
        .filter(pk=user_id)
        .first()
    )


def get_gallery_access_context(*, viewer, target):
    """
    Build common gallery access context.

    Access hierarchy:

        profile
            -> gallery
                -> album
                    -> photo
    """

    friendship = _get_friendship(
        viewer=viewer,
        target=target,
    )

    is_friend = friendship["is_friend"] if friendship else False

    profile_access = ProfileAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
    )

    gallery_access = GalleryAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
    )

    can_view_profile = profile_access.can_view_profile()

    can_view_gallery = can_view_profile and gallery_access.can_view_gallery()

    return {
        "friendship": friendship,
        "is_friend": is_friend,
        "is_owner": gallery_access.is_owner,
        "can_view_profile": can_view_profile,
        "can_view_gallery": can_view_gallery,
        "gallery_access": gallery_access,
    }


def get_gallery_stats(*, target, access):
    """
    Return counters for the gallery visible to the current viewer.

    Regular gallery counters exclude system albums such as
    Profile Photos.

    Storage usage still includes all photos owned by the user.
    """

    max_photos = settings.GALLERY_MAX_PHOTOS

    if not access["can_view_gallery"]:
        return {
            "albums_count": 0,
            "photos_count": 0,
            "max_photos": max_photos,
            "remaining_slots": 0,
            "used_slots": 0,
        }

    albums = UserAlbum.objects.filter(
        user=target,
        album_type=UserAlbum.AlbumType.PHOTO,
        purpose=UserAlbum.Purpose.USER,
    )

    albums = access["gallery_access"].filter_albums(
        albums,
    )

    photos = Photo.objects.filter(
        album__user=target,
        album__album_type=UserAlbum.AlbumType.PHOTO,
        album__purpose=UserAlbum.Purpose.USER,
    )

    photos = access["gallery_access"].filter_photos(
        photos,
    )

    if access["is_owner"]:
        remaining_slots = get_remaining_slots(target)
        used_slots = max(
            0,
            max_photos - remaining_slots,
        )
    else:
        remaining_slots = 0
        used_slots = 0

    return {
        "albums_count": albums.count(),
        "photos_count": photos.count(),
        "max_photos": max_photos,
        "remaining_slots": remaining_slots,
        "used_slots": used_slots,
    }


def _get_friendship(*, viewer, target):
    """
    Return friendship state for authenticated viewers.
    """

    if not viewer.is_authenticated:
        return None

    return FriendshipService.get_relation(
        viewer,
        target,
    )
