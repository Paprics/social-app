# src/gallery/tests/test_photo_comment_views.py

import pytest
from django.urls import reverse

from posts.models import Comment
from users.models.preferences import UserSettings


def comment_url(name, *, photo, comment=None):
    kwargs = {
        "photo_pk": photo.pk,
    }

    if comment is not None:
        kwargs["comment_id"] = comment.pk

    return reverse(
        f"gallery:{name}",
        kwargs=kwargs,
    )


@pytest.mark.django_db
class TestPhotoCommentListView:
    def test_authenticated_user_can_view_comments(
        self,
        client,
        gallery_other,
        gallery_photo,
        photo_comment,
    ):
        client.force_login(gallery_other)

        response = client.get(
            comment_url(
                "photo_comment_list",
                photo=gallery_photo,
            )
        )

        assert response.status_code == 200
        assert photo_comment.content in response.content.decode()

    def test_owner_can_view_existing_comments_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_owner)

        response = client.get(
            comment_url(
                "photo_comment_list",
                photo=gallery_photo,
            )
        )

        content = response.content.decode()

        assert response.status_code == 200
        assert photo_comment.content in content
        assert "Comments are disabled." in content
        assert "Only you can see existing comments." in content

    def test_other_user_cannot_view_comments_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_other)

        response = client.get(
            comment_url(
                "photo_comment_list",
                photo=gallery_photo,
            )
        )

        assert response.status_code == 403

    def test_existing_comments_survive_disable_and_reenable(
        self,
        client,
        gallery_owner,
        gallery_other,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        assert Comment.objects.filter(pk=photo_comment.pk).exists()

        client.force_login(gallery_other)

        response = client.get(
            comment_url(
                "photo_comment_list",
                photo=gallery_photo,
            )
        )

        assert response.status_code == 403

        gallery_owner.settings.comments_enabled = True
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        response = client.get(
            comment_url(
                "photo_comment_list",
                photo=gallery_photo,
            )
        )

        assert response.status_code == 200
        assert photo_comment.content in response.content.decode()
        assert Comment.objects.filter(pk=photo_comment.pk).exists()


@pytest.mark.django_db
class TestPhotoCommentCreateView:
    def test_user_can_create_photo_comment(
        self,
        client,
        gallery_other,
        gallery_photo,
    ):
        client.force_login(gallery_other)

        response = client.post(
            comment_url(
                "photo_comment_create",
                photo=gallery_photo,
            ),
            {
                "content": "New photo comment",
            },
        )

        assert response.status_code == 200

        assert Comment.objects.filter(
            photo=gallery_photo,
            author=gallery_other,
            parent__isnull=True,
            content="New photo comment",
        ).exists()

    def test_owner_cannot_create_comment_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_photo,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_owner)

        response = client.post(
            comment_url(
                "photo_comment_create",
                photo=gallery_photo,
            ),
            {
                "content": "Owner forbidden photo comment",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            photo=gallery_photo,
            content="Owner forbidden photo comment",
        ).exists()

    def test_comments_disabled_overrides_everyone_permission(
        self,
        client,
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

        client.force_login(gallery_other)

        response = client.post(
            comment_url(
                "photo_comment_create",
                photo=gallery_photo,
            ),
            {
                "content": "Forbidden while disabled",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            photo=gallery_photo,
            content="Forbidden while disabled",
        ).exists()


@pytest.mark.django_db
class TestPhotoCommentReplyView:
    def test_user_can_reply_to_root_comment(
        self,
        client,
        gallery_other,
        gallery_stranger,
        gallery_photo,
        photo_comment,
    ):
        client.force_login(gallery_stranger)

        response = client.post(
            comment_url(
                "photo_comment_reply",
                photo=gallery_photo,
                comment=photo_comment,
            ),
            {
                "content": "Photo reply",
            },
        )

        assert response.status_code == 200

        assert Comment.objects.filter(
            photo=gallery_photo,
            author=gallery_stranger,
            parent=photo_comment,
            content="Photo reply",
        ).exists()

    def test_owner_cannot_reply_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_owner)

        response = client.post(
            comment_url(
                "photo_comment_reply",
                photo=gallery_photo,
                comment=photo_comment,
            ),
            {
                "content": "Forbidden owner reply",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            photo=gallery_photo,
            parent=photo_comment,
            content="Forbidden owner reply",
        ).exists()

    def test_other_user_cannot_reply_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_stranger,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_stranger)

        response = client.post(
            comment_url(
                "photo_comment_reply",
                photo=gallery_photo,
                comment=photo_comment,
            ),
            {
                "content": "Forbidden outsider reply",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            photo=gallery_photo,
            parent=photo_comment,
            content="Forbidden outsider reply",
        ).exists()


@pytest.mark.django_db
class TestPhotoCommentUpdateView:
    def test_comment_author_can_update_when_comments_enabled(
        self,
        client,
        gallery_other,
        gallery_photo,
        photo_comment,
    ):
        client.force_login(gallery_other)

        response = client.post(
            comment_url(
                "photo_comment_update",
                photo=gallery_photo,
                comment=photo_comment,
            ),
            {
                "content": "Updated photo comment",
            },
        )

        assert response.status_code == 200

        photo_comment.refresh_from_db()

        assert photo_comment.content == "Updated photo comment"

    def test_other_comment_author_cannot_update_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_other,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_other)

        response = client.post(
            comment_url(
                "photo_comment_update",
                photo=gallery_photo,
                comment=photo_comment,
            ),
            {
                "content": "Forbidden edit",
            },
        )

        assert response.status_code == 403

        photo_comment.refresh_from_db()

        assert photo_comment.content == "Initial photo comment"

    def test_owner_can_update_own_existing_comment_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_photo,
        owner_photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_owner)

        response = client.post(
            comment_url(
                "photo_comment_update",
                photo=gallery_photo,
                comment=owner_photo_comment,
            ),
            {
                "content": "Updated owner comment",
            },
        )

        assert response.status_code == 200

        owner_photo_comment.refresh_from_db()

        assert owner_photo_comment.content == "Updated owner comment"


@pytest.mark.django_db
class TestPhotoCommentDeleteView:
    def test_comment_author_can_delete_when_comments_enabled(
        self,
        client,
        gallery_other,
        gallery_photo,
        photo_comment,
    ):
        comment_id = photo_comment.pk

        client.force_login(gallery_other)

        response = client.post(
            comment_url(
                "photo_comment_delete",
                photo=gallery_photo,
                comment=photo_comment,
            )
        )

        assert response.status_code == 200
        assert not Comment.objects.filter(pk=comment_id).exists()

    def test_other_comment_author_cannot_delete_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_other,
        gallery_photo,
        photo_comment,
    ):
        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_other)

        response = client.post(
            comment_url(
                "photo_comment_delete",
                photo=gallery_photo,
                comment=photo_comment,
            )
        )

        assert response.status_code == 403
        assert Comment.objects.filter(pk=photo_comment.pk).exists()

    def test_owner_can_delete_own_existing_comment_when_comments_disabled(
        self,
        client,
        gallery_owner,
        gallery_photo,
        owner_photo_comment,
    ):
        comment_id = owner_photo_comment.pk

        gallery_owner.settings.comments_enabled = False
        gallery_owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(gallery_owner)

        response = client.post(
            comment_url(
                "photo_comment_delete",
                photo=gallery_photo,
                comment=owner_photo_comment,
            )
        )

        assert response.status_code == 200
        assert not Comment.objects.filter(pk=comment_id).exists()

    def test_photo_owner_cannot_delete_somebody_elses_comment(
        self,
        client,
        gallery_owner,
        gallery_photo,
        photo_comment,
    ):
        client.force_login(gallery_owner)

        response = client.post(
            comment_url(
                "photo_comment_delete",
                photo=gallery_photo,
                comment=photo_comment,
            )
        )

        assert response.status_code == 403
        assert Comment.objects.filter(pk=photo_comment.pk).exists()
