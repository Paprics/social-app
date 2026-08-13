# src/gallery/selectors/photos.py

from django.contrib.auth import get_user_model

from gallery.models import Photo, UserAlbum

User = get_user_model()


def get_avatar_candidate_photos(*, user):
    """
    Return user photos available for avatar selection.

    Avatar selection is an owner-only flow and may include photos
    from both regular and system albums.
    """

    return (
        Photo.objects.filter(
            album__user=user,
            is_visible=True,
        )
        .select_related(
            "album",
        )
        .order_by(
            "-created_at",
        )
    )


def get_photo_target_user(*, photo_id):
    """
    Return the owner of a photo with relations required for access checks.

    The photo may still be rejected later by get_photo_for_view(), for
    example when it belongs to a system album or is not visible to viewer.
    """

    return (
        User.objects.select_related(
            "profile",
            "settings",
        )
        .filter(
            galleries__photos__pk=photo_id,
        )
        .first()
    )


def get_gallery_photos(
    *,
    target,
    access,
):
    """
    Return all regular gallery photos available to the current viewer.

    System albums such as Profile Photos are excluded.

    Pagination is intentionally not performed here.
    """

    if not access["can_view_gallery"]:
        return Photo.objects.none()

    photos = Photo.objects.filter(
        album__user=target,
        album__album_type=UserAlbum.AlbumType.PHOTO,
        album__purpose=UserAlbum.Purpose.USER,
    ).select_related(
        "album",
    )

    photos = access["gallery_access"].filter_photos(
        photos,
    )

    return photos.order_by(
        "-created_at",
    )


def get_album_photos(
    *,
    album,
    access,
):
    """
    Return photos from one album available to the current viewer.

    The album itself should normally be obtained through
    get_album_for_view().
    """

    if not access["can_view_gallery"]:
        return Photo.objects.none()

    if not access["gallery_access"].can_view_album(
        album,
    ):
        return Photo.objects.none()

    photos = Photo.objects.filter(
        album=album,
    ).select_related(
        "album",
    )

    photos = access["gallery_access"].filter_photos(
        photos,
    )

    return photos.order_by(
        "-created_at",
    )


def get_photo_for_view(
    *,
    target,
    photo_id,
    access,
):
    """
    Return one regular gallery photo when the viewer may access it.

    Returns None when:
    - the photo does not exist;
    - it belongs to another user;
    - it belongs to a system album;
    - profile/gallery access is denied;
    - album access is denied;
    - photo visibility denies access.
    """

    if not access["can_view_gallery"]:
        return None

    photo = (
        Photo.objects.select_related(
            "album",
            "album__user",
        )
        .filter(
            pk=photo_id,
            album__user=target,
            album__album_type=UserAlbum.AlbumType.PHOTO,
            album__purpose=UserAlbum.Purpose.USER,
        )
        .first()
    )

    if photo is None:
        return None

    if not access["gallery_access"].can_view_photo(
        photo,
    ):
        return None

    return photo
