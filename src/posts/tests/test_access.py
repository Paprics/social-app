# src/posts/tests/test_access.py

import pytest
from django.contrib.auth.models import AnonymousUser

from posts.services.access.comment import CommentAccessService
from posts.services.access.post import PostAccessService
from users.models.preferences import UserSettings


@pytest.mark.django_db
class TestPostAccessService:
    def test_wall_is_visible_when_profile_and_wall_are_enabled(
        self,
        owner,
        other,
    ):
        access = PostAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_view_wall() is True

    def test_wall_is_hidden_for_anonymous_user(
        self,
        owner,
    ):
        access = PostAccessService(
            viewer=AnonymousUser(),
            target=owner,
            can_view_profile=True,
        )

        assert access.can_view_wall() is False

    def test_wall_is_hidden_when_profile_is_not_visible(
        self,
        owner,
        other,
    ):
        access = PostAccessService(
            viewer=other,
            target=owner,
            can_view_profile=False,
        )

        assert access.can_view_wall() is False

    def test_wall_is_hidden_when_wall_disabled(
        self,
        owner,
        other,
    ):
        owner.settings.wall_enabled = False
        owner.settings.save(update_fields=["wall_enabled"])

        access = PostAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_view_wall() is False

    def test_owner_can_post_on_own_wall(
        self,
        owner,
    ):
        access = PostAccessService(
            viewer=owner,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_post_on_wall() is True

    @pytest.mark.parametrize(
        ("access_level", "is_friend", "expected"),
        [
            (
                UserSettings.AccessLevel.EVERYONE,
                False,
                True,
            ),
            (
                UserSettings.AccessLevel.FRIENDS,
                True,
                True,
            ),
            (
                UserSettings.AccessLevel.FRIENDS,
                False,
                False,
            ),
            (
                UserSettings.AccessLevel.ONLY_ME,
                False,
                False,
            ),
        ],
    )
    def test_wall_post_permission(
        self,
        owner,
        other,
        access_level,
        is_friend,
        expected,
    ):
        owner.settings.wall_post_permission = access_level
        owner.settings.save(update_fields=["wall_post_permission"])

        access = PostAccessService(
            viewer=other,
            target=owner,
            is_friend=is_friend,
            can_view_profile=True,
        )

        assert access.can_post_on_wall() is expected

    def test_target_blocking_viewer_prevents_wall_post(
        self,
        owner,
        other,
    ):
        access = PostAccessService(
            viewer=other,
            target=owner,
            is_blocked=True,
            target_has_blocked=True,
            can_view_profile=True,
        )

        assert access.can_post_on_wall() is False

    def test_viewer_blocking_target_does_not_prevent_wall_post(
        self,
        owner,
        other,
    ):
        access = PostAccessService(
            viewer=other,
            target=owner,
            is_blocked=True,
            target_has_blocked=False,
            can_view_profile=True,
        )

        assert access.can_post_on_wall() is True

    def test_only_author_can_edit_post(
        self,
        owner,
        author,
        other,
        wall_post,
    ):
        author_access = PostAccessService(
            viewer=author,
            target=owner,
            can_view_profile=True,
        )

        other_access = PostAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert author_access.can_edit_post(wall_post) is True
        assert other_access.can_edit_post(wall_post) is False

    def test_author_can_delete_post(
        self,
        owner,
        author,
        wall_post,
    ):
        access = PostAccessService(
            viewer=author,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_post(wall_post) is True

    def test_wall_owner_can_delete_foreign_post(
        self,
        owner,
        wall_post,
    ):
        access = PostAccessService(
            viewer=owner,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_post(wall_post) is True

    def test_unrelated_user_cannot_delete_post(
        self,
        owner,
        other,
        wall_post,
    ):
        access = PostAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_post(wall_post) is False


@pytest.mark.django_db
class TestCommentAccessService:
    def test_everyone_can_comment_when_permission_is_everyone(
        self,
        owner,
        other,
        wall_post,
    ):
        owner.settings.comment_permission = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(update_fields=["comment_permission"])

        access = CommentAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_comment_on_post(wall_post) is True

    def test_only_friend_can_comment_when_permission_is_friends(
        self,
        owner,
        other,
        wall_post,
    ):
        owner.settings.comment_permission = UserSettings.AccessLevel.FRIENDS
        owner.settings.save(update_fields=["comment_permission"])

        friend_access = CommentAccessService(
            viewer=other,
            target=owner,
            is_friend=True,
            can_view_profile=True,
        )

        stranger_access = CommentAccessService(
            viewer=other,
            target=owner,
            is_friend=False,
            can_view_profile=True,
        )

        assert friend_access.can_comment_on_post(wall_post) is True
        assert stranger_access.can_comment_on_post(wall_post) is False

    def test_blocked_user_cannot_comment(
        self,
        owner,
        other,
        wall_post,
    ):
        access = CommentAccessService(
            viewer=other,
            target=owner,
            is_blocked=True,
            can_view_profile=True,
        )

        assert access.can_comment_on_post(wall_post) is False

    def test_only_comment_author_can_edit(
        self,
        owner,
        other,
        author,
        comment,
    ):
        author_access = CommentAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        another_access = CommentAccessService(
            viewer=author,
            target=owner,
            can_view_profile=True,
        )

        assert author_access.can_edit_comment(comment) is True
        assert another_access.can_edit_comment(comment) is False

    def test_comment_author_can_delete(
        self,
        owner,
        other,
        comment,
    ):
        access = CommentAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_comment(comment) is True

    def test_post_author_can_delete_comment(
        self,
        owner,
        author,
        comment,
    ):
        access = CommentAccessService(
            viewer=author,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_comment(comment) is True

    def test_wall_owner_can_delete_comment(
        self,
        owner,
        comment,
    ):
        access = CommentAccessService(
            viewer=owner,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_comment(comment) is True

    def test_owner_can_view_existing_comments_when_comments_disabled(
        self,
        owner,
        wall_post,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        access = CommentAccessService(
            viewer=owner,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_view_comments(wall_post) is True

    def test_other_user_cannot_view_comments_when_comments_disabled(
        self,
        owner,
        other,
        wall_post,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        access = CommentAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_view_comments(wall_post) is False

    def test_owner_cannot_create_comment_when_comments_disabled(
        self,
        owner,
        wall_post,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        access = CommentAccessService(
            viewer=owner,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_comment_on_post(wall_post) is False

    def test_other_user_cannot_comment_when_comments_disabled_even_if_permission_is_everyone(
        self,
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

        access = CommentAccessService(
            viewer=other,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_comment_on_post(wall_post) is False

    def test_wall_owner_can_delete_existing_comment_when_comments_disabled(
        self,
        owner,
        comment,
    ):
        owner.settings.comments_enabled = False
        owner.settings.save(update_fields=["comments_enabled"])

        access = CommentAccessService(
            viewer=owner,
            target=owner,
            can_view_profile=True,
        )

        assert access.can_delete_comment(comment) is True
