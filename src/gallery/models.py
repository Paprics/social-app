# src/gallery/models.py

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


def photo_upload_path(instance, filename):
    """Build storage path for a photo inside a user album."""
    return f"photos/users/" f"{instance.album.user_id}/" f"{instance.album_id}/" f"{filename}"


class UserAlbum(models.Model):
    """Photo or video album owned by a user."""

    class AlbumType(models.TextChoices):
        PHOTO = "photo", _("Photo")
        VIDEO = "video", _("Video")

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        FRIENDS = "friends", _("Friends only")
        PRIVATE = "private", _("Only me")

    class Purpose(models.TextChoices):
        """Internal role of the album."""

        USER = "user", _("User album")
        PROFILE_PHOTOS = "profile_photos", _("Profile photos")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="galleries",
        verbose_name=_("User"),
    )

    album_type = models.CharField(
        max_length=10,
        choices=AlbumType.choices,
        default=AlbumType.PHOTO,
        verbose_name=_("Album type"),
        help_text=_("Media type stored in this album."),
    )

    # Separates ordinary user albums from albums used by the system.
    purpose = models.CharField(
        max_length=32,
        choices=Purpose.choices,
        default=Purpose.USER,
        db_index=True,
        verbose_name=_("Purpose"),
        help_text=_("Internal purpose of this album."),
    )

    title = models.CharField(
        max_length=100,
        verbose_name=_("Title"),
        help_text=_("Album title."),
    )

    slug = models.SlugField(
        max_length=120,
        verbose_name=_("Slug"),
        help_text=_("Unique album identifier."),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional album description."),
    )

    # Default for ordinary user albums.
    # Profile Photos will explicitly use PRIVATE in its service.
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        verbose_name=_("Visibility"),
        help_text=_("Who can view this album."),
    )

    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("Visible"),
        help_text=_("Whether this album is visible."),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated"),
    )

    class Meta:
        ordering = ["title"]
        verbose_name = _("Photo album")
        verbose_name_plural = _("Photo albums")

        constraints = [
            # A user cannot have two albums with the same slug.
            models.UniqueConstraint(
                fields=["user", "slug"],
                name="unique_user_album_slug",
            ),
            # A user may have many ordinary albums,
            # but only one dedicated Profile Photos album.
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(purpose="profile_photos"),
                name="unique_profile_photos_album_per_user",
            ),
        ]

    def save(self, *args, **kwargs):
        """Generate slug from title when it was not supplied."""
        if not self.slug:
            self.slug = slugify(self.title)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Photo(models.Model):
    """Photo stored inside a user album."""

    album = models.ForeignKey(
        UserAlbum,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Album"),
    )

    image = models.ImageField(
        upload_to=photo_upload_path,
        verbose_name=_("Image"),
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Title"),
        help_text=_("Optional photo title."),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional photo description."),
    )

    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("Visible"),
        help_text=_("Whether this photo is visible."),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Photo")
        verbose_name_plural = _("Photos")

    def __str__(self):
        return self.title or f"Photo #{self.pk}"
