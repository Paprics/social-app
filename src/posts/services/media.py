# src/posts/services/media.py
"""Business operations for image attachments in wall posts."""

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from gallery.models import Photo, UserAlbum
from gallery.services.post_photos import PostPhotoService
from posts.models import PostMedia
from posts.services.access.media import PostMediaAccessService


class PostMediaError(Exception):
    """Base exception for post media operations."""


class PostMediaPermissionError(PostMediaError):
    """Raised when the user cannot manage media for the post."""


class PostMediaOwnershipError(PostMediaError):
    """Raised when the user attempts to attach another user's photo."""


class PostMediaLimitError(PostMediaError):
    """Raised when the post has reached its image limit."""


class PostMediaService:
    """Manage image attachments belonging to wall posts."""

    @staticmethod
    def get_max_images() -> int:
        """Return the configured maximum number of images per post."""
        return int(getattr(settings, "POST_MAX_IMAGES", 10))

    @classmethod
    def _check_access(cls, *, post, actor) -> None:
        """Ensure the actor may manage images for this post."""

        if not PostMediaAccessService.can_attach_images(
            user=actor,
            post=post,
        ):
            raise PostMediaPermissionError(
                "You cannot manage images for this post.",
            )

    @classmethod
    def _check_capacity(
        cls,
        *,
        post,
        additional=1,
    ) -> None:
        """Ensure the post has enough free image slots."""

        if additional <= 0:
            return

        current_count = post.media_items.count()
        max_images = cls.get_max_images()

        if current_count + additional > max_images:
            raise PostMediaLimitError(
                f"A post may contain at most {max_images} images.",
            )

    @staticmethod
    def _next_position(*, post) -> int:
        """Return the next display position for a post attachment."""

        last_position = post.media_items.aggregate(
            value=Max("position"),
        )["value"]

        if last_position is None:
            return 0

        return last_position + 1

    @staticmethod
    def _delete_storage_file(photo) -> None:
        """Delete the physical image file without touching the model."""

        if not photo.image:
            return

        name = photo.image.name

        if not name:
            return

        photo.image.storage.delete(name)

    @classmethod
    def _cleanup_post_photo_if_orphaned(cls, *, photo) -> None:
        """
        Delete an unused photo created specifically for posts.

        Photos originating from normal user albums or Profile Photos are never
        deleted here because they have an independent lifecycle in the gallery.
        """

        if photo.album.purpose != UserAlbum.Purpose.POST_PHOTOS:
            return

        if photo.post_media_items.exists():
            return

        storage = photo.image.storage
        image_name = photo.image.name

        photo.delete()

        # TODO: Cleanup generated easy-thumbnails files together with the source
        # image. Currently only the original processed image is deleted, so
        # derivatives such as *.640x640_q85.jpg may remain in storage.

        # Remove the physical file only after the database transaction commits.
        if image_name:
            transaction.on_commit(
                lambda: storage.delete(image_name),
            )

    @classmethod
    @transaction.atomic
    def attach_existing(
        cls,
        *,
        post,
        actor,
        photo,
    ) -> PostMedia:
        """Attach one existing photo owned by the post author."""

        cls._check_access(
            post=post,
            actor=actor,
        )

        if photo.album.user_id != actor.id:
            raise PostMediaOwnershipError(
                "You can only attach your own photos.",
            )

        existing = PostMedia.objects.filter(
            post=post,
            photo=photo,
        ).first()

        if existing:
            return existing

        cls._check_capacity(
            post=post,
            additional=1,
        )

        return PostMedia.objects.create(
            post=post,
            photo=photo,
            position=cls._next_position(post=post),
        )

    @classmethod
    @transaction.atomic
    def attach_existing_photos(
        cls,
        *,
        post,
        actor,
        photos,
    ) -> list[PostMedia]:
        """Attach several existing user photos to a post."""

        cls._check_access(
            post=post,
            actor=actor,
        )

        unique_photos = []
        seen_ids = set()

        for photo in photos:
            if photo.pk in seen_ids:
                continue

            seen_ids.add(photo.pk)
            unique_photos.append(photo)

        for photo in unique_photos:
            if photo.album.user_id != actor.id:
                raise PostMediaOwnershipError(
                    "You can only attach your own photos.",
                )

        existing_items = {
            media.photo_id: media
            for media in PostMedia.objects.filter(
                post=post,
                photo_id__in=[photo.pk for photo in unique_photos],
            )
        }

        new_photos = [photo for photo in unique_photos if photo.pk not in existing_items]

        cls._check_capacity(
            post=post,
            additional=len(new_photos),
        )

        position = cls._next_position(post=post)
        result = []

        for photo in unique_photos:
            existing = existing_items.get(photo.pk)

            if existing:
                result.append(existing)
                continue

            media = PostMedia.objects.create(
                post=post,
                photo=photo,
                position=position,
            )

            result.append(media)
            position += 1

        return result

    @classmethod
    def upload_file(
        cls,
        *,
        post,
        actor,
        file,
    ) -> PostMedia:
        """Upload one new photo and attach it to the post."""

        items = cls.upload_files(
            post=post,
            actor=actor,
            files=[file],
        )

        return items[0]

    @classmethod
    def upload_files(
        cls,
        *,
        post,
        actor,
        files,
    ) -> list[PostMedia]:
        """
        Upload several new photos and attach them to the post.

        New uploads are stored in the author's private system Post Photos
        album. Database changes are atomic, while created storage files are
        explicitly removed if the operation fails partway through.
        """

        files = list(files)

        if not files:
            return []

        cls._check_access(
            post=post,
            actor=actor,
        )

        cls._check_capacity(
            post=post,
            additional=len(files),
        )

        created_photos = []

        try:
            with transaction.atomic():
                position = cls._next_position(post=post)
                media_items = []

                for file in files:
                    photo = PostPhotoService.create_photo(
                        user=actor,
                        file=file,
                    )
                    created_photos.append(photo)

                    media = PostMedia.objects.create(
                        post=post,
                        photo=photo,
                        position=position,
                    )

                    media_items.append(media)
                    position += 1

                return media_items

        except Exception:
            # The DB transaction rolls rows back, but storage files are not
            # transactional, so files already written must be removed manually.
            for photo in created_photos:
                cls._delete_storage_file(photo)

            raise

    @classmethod
    @transaction.atomic
    def remove(
        cls,
        *,
        media,
        actor,
    ) -> None:
        """Remove one image attachment from a post."""

        post = media.post
        photo = media.photo

        cls._check_access(
            post=post,
            actor=actor,
        )

        media.delete()

        cls._cleanup_post_photo_if_orphaned(
            photo=photo,
        )

    @staticmethod
    def collect_cleanup_photos(*, post) -> list[Photo]:
        """
        Collect system post photos before deleting a post.

        The relations themselves disappear through CASCADE, so photos that may
        need cleanup must be remembered before the Post row is deleted.
        """

        return [
            media.photo
            for media in post.media_items.select_related(
                "photo__album",
            )
            if media.photo.album.purpose == UserAlbum.Purpose.POST_PHOTOS
        ]

    @classmethod
    def cleanup_photos(cls, *, photos) -> None:
        """Delete collected system photos that no longer belong to any post."""

        for photo in photos:
            cls._cleanup_post_photo_if_orphaned(
                photo=photo,
            )
