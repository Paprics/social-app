# src/posts/tests/test_post_views.py

import pytest
from django.urls import reverse

from posts.models import Post
from users.models.preferences import UserSettings


@pytest.mark.django_db
class TestWallPostsView:
    def test_wall_requires_authentication(
        self,
        client,
        owner,
    ):
        response = client.get(
            reverse(
                "posts:wall_posts",
                kwargs={"user_id": owner.pk},
            )
        )

        assert response.status_code == 302

    def test_authenticated_user_can_view_public_wall(
        self,
        client,
        owner,
        other,
    ):
        client.force_login(other)

        response = client.get(
            reverse(
                "posts:wall_posts",
                kwargs={"user_id": owner.pk},
            )
        )

        assert response.status_code == 200

    def test_direct_wall_endpoint_respects_profile_privacy(
        self,
        client,
        owner,
        other,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(update_fields=["profile_visibility"])

        client.force_login(other)

        response = client.get(
            reverse(
                "posts:wall_posts",
                kwargs={"user_id": owner.pk},
            )
        )

        assert response.status_code == 403

    def test_wall_disabled_returns_403(
        self,
        client,
        owner,
        other,
    ):
        owner.settings.wall_enabled = False
        owner.settings.save(update_fields=["wall_enabled"])

        client.force_login(other)

        response = client.get(
            reverse(
                "posts:wall_posts",
                kwargs={"user_id": owner.pk},
            )
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestCreatePostView:
    def test_user_can_create_post_when_allowed(
        self,
        client,
        owner,
        author,
    ):
        client.force_login(author)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "New post",
            },
        )

        assert response.status_code == 200

        post = Post.objects.get(
            owner=owner,
            author=author,
        )

        assert post.content == "New post"

    def test_user_cannot_create_post_when_permission_only_me(
        self,
        client,
        owner,
        author,
    ):
        owner.settings.wall_post_permission = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(update_fields=["wall_post_permission"])

        client.force_login(author)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Forbidden post",
            },
        )

        assert response.status_code == 403

        assert not Post.objects.filter(
            owner=owner,
            author=author,
            content="Forbidden post",
        ).exists()

    def test_blank_post_returns_400(
        self,
        client,
        owner,
        author,
    ):
        client.force_login(author)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "   ",
            },
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestUpdatePostView:
    def test_author_can_update_post(
        self,
        client,
        author,
        wall_post,
    ):
        client.force_login(author)

        response = client.post(
            reverse(
                "posts:update",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "Updated content",
            },
        )

        assert response.status_code == 200

        wall_post.refresh_from_db()

        assert wall_post.content == "Updated content"

    def test_unrelated_user_cannot_update_post(
        self,
        client,
        other,
        wall_post,
    ):
        client.force_login(other)

        response = client.post(
            reverse(
                "posts:update",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "Hacked content",
            },
        )

        assert response.status_code == 403

        wall_post.refresh_from_db()

        assert wall_post.content == "Initial post content"

    def test_blank_update_keeps_original_content(
        self,
        client,
        author,
        wall_post,
    ):
        client.force_login(author)

        response = client.post(
            reverse(
                "posts:update",
                kwargs={"post_id": wall_post.pk},
            ),
            {
                "content": "   ",
            },
        )

        assert response.status_code == 200

        wall_post.refresh_from_db()

        assert wall_post.content == "Initial post content"


@pytest.mark.django_db
class TestDeletePostView:
    def test_post_author_can_delete(
        self,
        client,
        author,
        wall_post,
    ):
        post_id = wall_post.pk

        client.force_login(author)

        response = client.delete(
            reverse(
                "posts:delete",
                kwargs={"post_id": post_id},
            )
        )

        assert response.status_code == 200
        assert not Post.objects.filter(pk=post_id).exists()

    def test_wall_owner_can_delete_foreign_post(
        self,
        client,
        owner,
        wall_post,
    ):
        post_id = wall_post.pk

        client.force_login(owner)

        response = client.delete(
            reverse(
                "posts:delete",
                kwargs={"post_id": post_id},
            )
        )

        assert response.status_code == 200
        assert not Post.objects.filter(pk=post_id).exists()

    def test_unrelated_user_cannot_delete_post(
        self,
        client,
        other,
        wall_post,
    ):
        client.force_login(other)

        response = client.delete(
            reverse(
                "posts:delete",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 403
        assert Post.objects.filter(pk=wall_post.pk).exists()


@pytest.mark.django_db
class TestPostDetailView:
    def test_post_detail_returns_one_post(
        self,
        client,
        author,
        wall_post,
    ):
        client.force_login(author)

        response = client.get(
            reverse(
                "posts:detail",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 200
        assert str(wall_post.pk) in response.content.decode()

    def test_post_detail_is_hidden_when_wall_disabled(
        self,
        client,
        owner,
        author,
        wall_post,
    ):
        owner.settings.wall_enabled = False
        owner.settings.save(update_fields=["wall_enabled"])

        client.force_login(author)

        response = client.get(
            reverse(
                "posts:detail",
                kwargs={"post_id": wall_post.pk},
            )
        )

        assert response.status_code == 403
