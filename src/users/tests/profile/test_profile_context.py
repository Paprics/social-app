# src/users/tests/profile/test_profile_context.py

from unittest.mock import Mock

import pytest
from django.http import Http404
from django.test import RequestFactory

from users.models.friendship import Friendship
from users.models.preferences import UserSettings
from users.models.user_block import UserBlock
from users.services.profile_context import ProfileContextBuilder


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.django_db
class TestProfileContextContract:
    def test_context_has_expected_contract(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        request = request_factory.get("/")
        request.user = stranger

        monkeypatch.setattr(
            "users.services.profile_context.content.get_profile_albums",
            lambda **kwargs: ([], 0),
        )

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert set(context) == {
            "target_user",
            "is_owner",
            "access",
            "albums",
            "albums_count",
            "friendship",
            "friends",
            "friends_count",
            "mutual_friends",
            "mutual_friends_count",
            "favorite_url",
            "is_favorite",
            "is_blocked",
            "viewer_has_blocked",
            "target_has_blocked",
        }

        assert context["target_user"].pk == owner.pk
        assert context["is_owner"] is False

        assert set(context["access"]) == {
            "can_view_profile",
            "can_view_friends",
            "can_send_message",
            "can_view_wall",
            "can_post_on_wall",
        }

    def test_missing_profile_returns_404(
        self,
        request_factory,
        stranger,
    ):
        request = request_factory.get("/")
        request.user = stranger

        with pytest.raises(Http404):
            ProfileContextBuilder.build_profile(
                request,
                999999999,
            )


@pytest.mark.django_db
class TestProfileContextAccessHierarchy:
    def test_private_profile_closes_child_resources(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.photo_albums_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.wall_enabled = True
        owner.settings.wall_post_permission = UserSettings.AccessLevel.EVERYONE

        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
                "photo_albums_visibility",
                "wall_enabled",
                "wall_post_permission",
            ]
        )

        request = request_factory.get("/")
        request.user = stranger

        gallery_mock = Mock(side_effect=AssertionError("Gallery selector must not be called for a closed profile."))

        friends_preview_mock = Mock(
            side_effect=AssertionError("Friends preview must not be loaded for a closed profile.")
        )

        friends_count_mock = Mock(side_effect=AssertionError("Friends count must not be loaded for a closed profile."))

        mutual_mock = Mock(side_effect=AssertionError("Mutual friends must not be loaded for a closed profile."))

        monkeypatch.setattr(
            "users.services.profile_context.content.get_profile_albums",
            gallery_mock,
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_friends_preview",
            friends_preview_mock,
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_friends_count",
            friends_count_mock,
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_mutual_friends",
            mutual_mock,
        )

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["access"]["can_view_profile"] is False
        assert context["access"]["can_view_friends"] is False
        assert context["access"]["can_view_wall"] is False
        assert context["access"]["can_post_on_wall"] is False

        assert context["albums"] == []
        assert context["albums_count"] == 0

        assert context["friends"] == []
        assert context["friends_count"] == 0

        assert context["mutual_friends"] == []
        assert context["mutual_friends_count"] == 0

        gallery_mock.assert_not_called()
        friends_preview_mock.assert_not_called()
        friends_count_mock.assert_not_called()
        mutual_mock.assert_not_called()

    def test_wall_disabled_overrides_wall_post_permission(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.wall_enabled = False
        owner.settings.wall_post_permission = UserSettings.AccessLevel.EVERYONE

        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "wall_enabled",
                "wall_post_permission",
            ]
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_profile_albums",
            lambda **kwargs: ([], 0),
        )

        request = request_factory.get("/")
        request.user = stranger

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["access"]["can_view_profile"] is True
        assert context["access"]["can_view_wall"] is False
        assert context["access"]["can_post_on_wall"] is False


@pytest.mark.django_db
class TestProfileContextFriendship:
    def test_accepted_friend_gets_friends_only_profile_access(
        self,
        request_factory,
        owner,
        friend,
        monkeypatch,
    ):
        Friendship.objects.create(
            from_user=owner,
            to_user=friend,
            status=Friendship.Status.ACCEPTED,
        )

        owner.settings.profile_visibility = UserSettings.AccessLevel.FRIENDS
        owner.settings.friends_visibility = UserSettings.AccessLevel.FRIENDS

        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_profile_albums",
            lambda **kwargs: ([], 0),
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_friends_preview",
            lambda *args, **kwargs: [],
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_friends_count",
            lambda *args, **kwargs: 0,
        )

        request = request_factory.get("/")
        request.user = friend

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["friendship"]["is_friend"] is True
        assert context["access"]["can_view_profile"] is True
        assert context["access"]["can_view_friends"] is True

    def test_pending_request_does_not_grant_friend_access(
        self,
        request_factory,
        owner,
        stranger,
    ):
        Friendship.objects.create(
            from_user=stranger,
            to_user=owner,
            status=Friendship.Status.PENDING,
        )

        owner.settings.profile_visibility = UserSettings.AccessLevel.FRIENDS
        owner.settings.friends_visibility = UserSettings.AccessLevel.FRIENDS

        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        request = request_factory.get("/")
        request.user = stranger

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["friendship"]["is_friend"] is False
        assert context["friendship"]["outgoing_request"] is True

        assert context["access"]["can_view_profile"] is False
        assert context["access"]["can_view_friends"] is False


@pytest.mark.django_db
class TestProfileContextBlocking:
    def test_target_blocking_viewer_hides_profile(
        self,
        request_factory,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(update_fields=["profile_visibility"])

        UserBlock.objects.create(
            blocker=owner,
            blocked=stranger,
        )

        request = request_factory.get("/")
        request.user = stranger

        with pytest.raises(Http404):
            ProfileContextBuilder.build_profile(
                request,
                owner.pk,
            )

    def test_viewer_blocking_target_keeps_normal_target_access(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.message_permission = UserSettings.AccessLevel.EVERYONE
        owner.settings.wall_enabled = True
        owner.settings.wall_post_permission = UserSettings.AccessLevel.EVERYONE

        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
                "message_permission",
                "wall_enabled",
                "wall_post_permission",
            ]
        )

        UserBlock.objects.create(
            blocker=stranger,
            blocked=owner,
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_profile_albums",
            lambda **kwargs: ([], 0),
        )

        request = request_factory.get("/")
        request.user = stranger

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["is_blocked"] is True
        assert context["viewer_has_blocked"] is True
        assert context["target_has_blocked"] is False

        assert context["access"]["can_view_profile"] is True
        assert context["access"]["can_view_friends"] is True
        assert context["access"]["can_send_message"] is True
        assert context["access"]["can_view_wall"] is True
        assert context["access"]["can_post_on_wall"] is True


@pytest.mark.django_db
class TestAnonymousProfileContext:
    def test_anonymous_public_profile_context(
        self,
        request_factory,
        owner,
        monkeypatch,
    ):
        from django.contrib.auth.models import AnonymousUser

        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE

        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_profile_albums",
            lambda **kwargs: ([], 0),
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_friends_preview",
            lambda *args, **kwargs: [],
        )

        monkeypatch.setattr(
            "users.services.profile_context.content.get_friends_count",
            lambda *args, **kwargs: 0,
        )

        request = request_factory.get("/")
        request.user = AnonymousUser()

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["friendship"] is None
        assert context["is_owner"] is False
        assert context["is_favorite"] is False
        assert context["is_blocked"] is False

        assert context["access"]["can_view_profile"] is True
        assert context["access"]["can_view_friends"] is True
        assert context["access"]["can_send_message"] is False
        assert context["access"]["can_view_wall"] is False
        assert context["access"]["can_post_on_wall"] is False
