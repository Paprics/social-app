# src/gallery/tests/test_photo_comment_access.py

import pytest

from gallery.services.access import GalleryAccessService
from gallery.services.photo_comment_access import PhotoCommentAccessService
from users.models.preferences import UserSettings


def build_access(
    *,
    viewer,
    target,
    is_friend=False,
    is_blocked=False,
    can_view_profile=True,
):
    gallery_access = GalleryAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
    )

    return PhotoCommentAccessService(
        viewer=viewer,
        target=target,
        gallery_access=gallery_access,
        is_friend=is_friend,
        is_blocked=is_blocked,
        can_view_profile=can_view_profile,
    )


@pytest.mark.django_db
class TestPhotoCommentAccessService:
    def test_other_user_can_view_comments_when_comments_enabled(
        self,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        access = build_access(
            viewer=gallery_other,
            target=gallery_owner,
        )

        assert access.can_view_comments(gallery_photo) is True

    def test_owner_can_view_existing_comments_when_comments_disabled(
        self,
        gallery_owner,
        gallery_photo,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_owner,
            target=gallery_owner,
        )

        assert access.can_view_comments(gallery_photo) is True

    def test_other_user_cannot_view_comments_when_comments_disabled(
        self,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_other,
            target=gallery_owner,
        )

        assert access.can_view_comments(gallery_photo) is False

    def test_owner_cannot_create_comment_when_comments_disabled(
        self,
        gallery_owner,
        gallery_photo,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_owner,
            target=gallery_owner,
        )

        assert access.can_comment_on_photo(gallery_photo) is False

    def test_comments_disabled_overrides_everyone_permission(
        self,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.comment_permission = UserSettings.AccessLevel.EVERYONE
        gallery_owner.settings.save(
            update_fields=[
                "comments_enabled",
                "comment_permission",
            ]
        )

        access = build_access(
            viewer=gallery_other,
            target=gallery_owner,
        )

        assert access.can_comment_on_photo(gallery_photo) is False

    def test_owner_cannot_reply_when_comments_disabled(
        self,
        gallery_owner,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_owner,
            target=gallery_owner,
        )

        assert (
            access.can_reply_to_comment(
                photo=gallery_photo,
                comment=photo_comment,
            )
            is False
        )

    def test_other_comment_author_cannot_edit_when_comments_disabled(
        self,
        gallery_owner,
        gallery_other,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_other,
            target=gallery_owner,
        )

        assert access.can_edit_comment(photo_comment) is False

    def test_other_comment_author_cannot_delete_when_comments_disabled(
        self,
        gallery_owner,
        gallery_other,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_other,
            target=gallery_owner,
        )

        assert access.can_delete_comment(photo_comment) is False

    def test_owner_can_edit_own_existing_comment_when_comments_disabled(
        self,
        gallery_owner,
        owner_photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_owner,
            target=gallery_owner,
        )

        assert access.can_edit_comment(owner_photo_comment) is True

    def test_owner_can_delete_own_existing_comment_when_comments_disabled(
        self,
        gallery_owner,
        owner_photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        access = build_access(
            viewer=gallery_owner,
            target=gallery_owner,
        )

        assert access.can_delete_comment(owner_photo_comment) is True

    def test_photo_owner_cannot_delete_somebody_elses_comment(
        self,
        gallery_owner,
        photo_comment,
    ):
        access = build_access(
            viewer=gallery_owner,
            target=gallery_owner,
        )

        assert access.can_delete_comment(photo_comment) is False
