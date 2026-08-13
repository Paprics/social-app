# src/posts/tests/test_comment_views.py

import pytest
from django.urls import reverse

from posts.models import Comment
from users.models.preferences import UserSettings


@pytest.mark.django_db
class TestCommentListView:
    def test_comment_list_requires_authentication(
        self,
        client,
        wall_post,
    ):
        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 302

    def test_authenticated_user_can_view_comments(
        self,
        client,
        author,
        wall_post,
        comment,
    ):
        client.force_login(author)

        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 200
        assert comment.content in response.content.decode()

    def test_comments_are_hidden_with_private_profile(
        self,
        client,
        owner,
        other,
        wall_post,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(update_fields=["profile_visibility"])

        client.force_login(other)

        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 403

    def test_owner_can_view_existing_comments_when_comments_disabled(
        self,
        client,
        owner,
        wall_post,
        comment,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(owner)

        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 200
        assert comment.content in response.content.decode()
        assert "Comments are disabled." in response.content.decode()

    def test_other_user_cannot_view_comments_when_comments_disabled(
        self,
        client,
        owner,
        other,
        wall_post,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(other)

        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 403

    def test_existing_comments_survive_disable_and_reenable(
        self,
        client,
        owner,
        other,
        wall_post,
        comment,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        assert Comment.objects.filter(pk=comment.pk).exists()

        client.force_login(other)

        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 403

        owner.settings.comments_enabled = True
        owner.settings.save(update_fields=["comments_enabled"])

        response = client.get(
            reverse(
                "posts:comment_list",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 200
        assert comment.content in response.content.decode()
        assert Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
class TestCommentCreateView:
    def test_user_can_create_comment(
        self,
        client,
        other,
        wall_post,
    ):
        client.force_login(other)

        response = client.post(
            reverse(
                "posts:comment_create",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "New comment",
            },
        )

        assert response.status_code == 200

        assert Comment.objects.filter(
            post=wall_post,
            author=other,
            content="New comment",
        ).exists()

    def test_blank_comment_returns_400(
        self,
        client,
        other,
        wall_post,
    ):
        client.force_login(other)

        response = client.post(
            reverse(
                "posts:comment_create",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "   ",
            },
        )

        assert response.status_code == 400

    def test_comment_permission_only_me_blocks_other_user(
        self,
        client,
        owner,
        other,
        wall_post,
    ):
        owner.settings.comment_permission = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(update_fields=["comment_permission"])

        client.force_login(other)

        response = client.post(
            reverse(
                "posts:comment_create",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "Forbidden comment",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            post=wall_post,
            content="Forbidden comment",
        ).exists()

    def test_owner_cannot_create_comment_when_comments_disabled(
        self,
        client,
        owner,
        wall_post,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        client.force_login(owner)

        response = client.post(
            reverse(
                "posts:comment_create",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "Owner forbidden comment",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            post=wall_post,
            content="Owner forbidden comment",
        ).exists()

    def test_comments_disabled_overrides_everyone_permission(
        self,
        client,
        owner,
        other,
        wall_post,
    ):
        owner.settings.comments_enabled = False
        owner.settings.comment_permission = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "comments_enabled",
                "comment_permission",
            ]
        )

        client.force_login(other)

        response = client.post(
            reverse(
                "posts:comment_create",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "Forbidden while disabled",
            },
        )

        assert response.status_code == 403

        assert not Comment.objects.filter(
            post=wall_post,
            content="Forbidden while disabled",
        ).exists()


@pytest.mark.django_db
class TestCommentUpdateView:
    def test_comment_author_can_update(
        self,
        client,
        other,
        comment,
    ):
        client.force_login(other)

        response = client.post(
            reverse(
                "posts:comment_update",
                kwargs={"comment_id": comment.pk},
            ),
            {
                "content": "Updated comment",
            },
        )

        assert response.status_code == 200

        comment.refresh_from_db()

        assert comment.content == "Updated comment"

    def test_other_user_cannot_update_comment(
        self,
        client,
        author,
        comment,
    ):
        client.force_login(author)

        response = client.post(
            reverse(
                "posts:comment_update",
                kwargs={"comment_id": comment.pk},
            ),
            {
                "content": "Unauthorized edit",
            },
        )

        assert response.status_code == 403

        comment.refresh_from_db()

        assert comment.content == "Initial comment"


@pytest.mark.django_db
class TestCommentDeleteView:
    def test_comment_author_can_delete(
        self,
        client,
        other,
        comment,
    ):
        comment_id = comment.pk

        client.force_login(other)

        response = client.delete(
            reverse(
                "posts:comment_delete",
                kwargs={"comment_id": comment_id},
            )
        )

        assert response.status_code == 200
        assert not Comment.objects.filter(pk=comment_id).exists()

    def test_post_author_can_delete_comment(
        self,
        client,
        author,
        comment,
    ):
        comment_id = comment.pk

        client.force_login(author)

        response = client.delete(
            reverse(
                "posts:comment_delete",
                kwargs={"comment_id": comment_id},
            )
        )

        assert response.status_code == 200
        assert not Comment.objects.filter(pk=comment_id).exists()

    def test_wall_owner_can_delete_comment(
        self,
        client,
        owner,
        comment,
    ):
        comment_id = comment.pk

        client.force_login(owner)

        response = client.delete(
            reverse(
                "posts:comment_delete",
                kwargs={"comment_id": comment_id},
            )
        )

        assert response.status_code == 200
        assert not Comment.objects.filter(pk=comment_id).exists()

    def test_unrelated_user_cannot_delete_comment(
        self,
        client,
        user_factory,
        comment,
    ):
        stranger = user_factory("stranger")

        client.force_login(stranger)

        response = client.delete(
            reverse(
                "posts:comment_delete",
                kwargs={"comment_id": comment.pk},
            )
        )

        assert response.status_code == 403
        assert Comment.objects.filter(pk=comment.pk).exists()
