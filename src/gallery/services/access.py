# src/gallery/services/access.py

from django.conf import settings

from gallery.models import Photo, UserAlbum
from users.models.preferences import UserSettings


class GalleryAccessService:
    """
    Central access rules for gallery resources.

    Access is evaluated from the broadest resource to the narrowest:

        gallery
            -> album
                -> photo

    A concrete album or photo must never bypass the user's global
    gallery access settings.
    """

    def __init__(self, *, viewer, target, is_friend=False):
        self.viewer = viewer
        self.target = target
        self.is_friend = bool(is_friend)

    @property
    def is_authenticated(self) -> bool:
        """Return whether the viewer is authenticated."""
        return self.viewer.is_authenticated

    @property
    def is_owner(self) -> bool:
        """Return whether the viewer owns the gallery."""
        return self.is_authenticated and self.viewer.pk == self.target.pk

    @property
    def allow_anonymous(self) -> bool:
        """
        Return whether anonymous users may access public gallery content.

        Disabled by default.

        Can be enabled later with:

            GALLERY_ALLOW_ANONYMOUS_VIEW = True
        """
        return settings.GALLERY_ALLOW_ANONYMOUS_VIEW

    @property
    def allowed_album_visibilities(self) -> tuple[str, ...]:
        """
        Return album visibility levels available to the current viewer.

        This property only describes album-level visibility.
        Global gallery access is checked separately.
        """

        if self.is_owner:
            return (
                UserAlbum.Visibility.PUBLIC,
                UserAlbum.Visibility.FRIENDS,
                UserAlbum.Visibility.PRIVATE,
            )

        if self.is_authenticated and self.is_friend:
            return (
                UserAlbum.Visibility.PUBLIC,
                UserAlbum.Visibility.FRIENDS,
            )

        if self.is_authenticated:
            return (UserAlbum.Visibility.PUBLIC,)

        if self.allow_anonymous:
            return (UserAlbum.Visibility.PUBLIC,)

        return ()

    def can_view_gallery(self) -> bool:
        """
        Return whether the viewer may access the user's gallery at all.

        This is the global gate for all gallery resources.
        """

        if self.is_owner:
            return True

        if not self.is_authenticated and not self.allow_anonymous:
            return False

        return self._check_access(
            self.target.settings.photo_albums_visibility,
        )

    def can_view_album(self, album: UserAlbum) -> bool:
        """
        Return whether the viewer may access a concrete album.

        Global gallery access is checked before album-level visibility.
        """

        if album.user_id != self.target.pk:
            return False

        if not self.can_view_gallery():
            return False

        if self.is_owner:
            return True

        if not album.is_visible:
            return False

        return album.visibility in self.allowed_album_visibilities

    def can_view_photo(self, photo: Photo) -> bool:
        """
        Return whether the viewer may access a concrete photo.

        A photo requires:
        - gallery access;
        - album access;
        - photo visibility.
        """

        if photo.album.user_id != self.target.pk:
            return False

        if not self.can_view_gallery():
            return False

        if self.is_owner:
            return True

        if not photo.is_visible:
            return False

        return self.can_view_album(photo.album)

    def filter_albums(self, queryset):
        """
        Filter albums according to the complete gallery access rules.

        The queryset may contain albums belonging to multiple users;
        it will always be restricted to the target user first.
        """

        queryset = queryset.filter(
            user=self.target,
        )

        if not self.can_view_gallery():
            return queryset.none()

        if self.is_owner:
            return queryset

        return queryset.filter(
            is_visible=True,
            visibility__in=self.allowed_album_visibilities,
        )

    def filter_photos(self, queryset):
        """
        Filter photos according to gallery, album and photo access rules.

        Intended for selectors that return lists of photos.
        """

        queryset = queryset.filter(
            album__user=self.target,
        )

        if not self.can_view_gallery():
            return queryset.none()

        if self.is_owner:
            return queryset

        return queryset.filter(
            is_visible=True,
            album__is_visible=True,
            album__visibility__in=self.allowed_album_visibilities,
        )

    def _check_access(self, access_level: str) -> bool:
        """
        Evaluate a global gallery access level for the current viewer.
        """

        if self.is_owner:
            return True

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return self.is_authenticated or self.allow_anonymous

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self.is_authenticated and self.is_friend

        return False
