# src/gallery/selectors/albums.py

from django.db.models import Count, Prefetch, Q

from gallery.models import Photo, UserAlbum
from gallery.services.access import GalleryAccessService


def get_profile_albums(
    *,
    viewer,
    target,
    is_friend=False,
    limit=3,
    preview_limit=4,
):
    """
    Return albums prepared for the profile-page preview.

    This selector intentionally returns only a small number of albums
    and a small photo preview for each album.
    """

    gallery_access = GalleryAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
    )

    albums = _get_user_albums(
        target=target,
    )

    albums = gallery_access.filter_albums(
        albums,
    )

    albums_count = albums.count()

    albums = _prepare_album_queryset(
        albums=albums,
        gallery_access=gallery_access,
        preview_limit=preview_limit,
    )

    return albums[:limit], albums_count


def get_gallery_albums(
    *,
    target,
    access,
):
    """
    Return all regular photo albums available to the current viewer.

    No pagination is performed here. The view is responsible for
    paginating the returned queryset.
    """

    if not access["can_view_gallery"]:
        return UserAlbum.objects.none()

    albums = _get_user_albums(
        target=target,
    )

    albums = access["gallery_access"].filter_albums(
        albums,
    )

    return _prepare_album_queryset(
        albums=albums,
        gallery_access=access["gallery_access"],
        preview_limit=1,
    )


def get_album_for_view(
    *,
    target,
    album_id,
    access,
):
    """
    Return one regular user album when the viewer may access it.

    Returns None when:
    - the album does not exist;
    - it belongs to another user;
    - it is a system album;
    - gallery access is denied;
    - album visibility denies access.
    """

    if not access["can_view_gallery"]:
        return None

    album = (
        _get_user_albums(
            target=target,
        )
        .select_related(
            "user",
        )
        .filter(
            pk=album_id,
        )
        .first()
    )

    if album is None:
        return None

    if not access["gallery_access"].can_view_album(
        album,
    ):
        return None

    return album


def _get_user_albums(*, target):
    """
    Return base queryset for regular user-created photo albums.

    System albums such as Profile Photos are deliberately excluded.
    """

    return UserAlbum.objects.filter(
        user=target,
        album_type=UserAlbum.AlbumType.PHOTO,
        purpose=UserAlbum.Purpose.USER,
    )


def _prepare_album_queryset(
    *,
    albums,
    gallery_access,
    preview_limit,
):
    """
    Add photo counts and prefetched preview photos to album queryset.
    """

    preview_photos = Photo.objects.order_by(
        "-created_at",
    )

    if gallery_access.is_owner:
        albums = albums.annotate(
            photos_count=Count(
                "photos",
            ),
        )
    else:
        preview_photos = preview_photos.filter(
            is_visible=True,
        )

        albums = albums.annotate(
            photos_count=Count(
                "photos",
                filter=Q(
                    photos__is_visible=True,
                ),
            ),
        )

    return albums.order_by(
        "-created_at",
    ).prefetch_related(
        Prefetch(
            "photos",
            queryset=preview_photos[:preview_limit],
            to_attr="preview_photos",
        ),
    )
