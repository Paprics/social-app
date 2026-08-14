# src/users/tests/profile/test_security_edges.py
"""Security edge-case tests for profile and gallery access."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import override_settings

from gallery.selectors.gallery import get_gallery_access_context
from users.models.preferences import UserSettings
from users.models.user_block import UserBlock
from users.services.access import ProfileAccessService
from users.services.profile_context import ProfileContextBuilder


@pytest.mark.django_db
class TestGalleryHierarchy:
    def test_private_profile_closes_public_gallery(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.photo_albums_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "photo_albums_visibility",
            ]
        )

        access = get_gallery_access_context(
            viewer=stranger,
            target=owner,
        )

        assert access["can_view_profile"] is False
        assert access["can_view_gallery"] is False

    def test_closed_gallery_stays_closed_on_public_profile(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.photo_albums_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "photo_albums_visibility",
            ]
        )

        access = get_gallery_access_context(
            viewer=stranger,
            target=owner,
        )

        assert access["can_view_profile"] is True
        assert access["can_view_gallery"] is False

    @override_settings(GALLERY_ALLOW_ANONYMOUS_VIEW=False)
    def test_anonymous_public_profile_does_not_bypass_gallery_policy(
        self,
        owner,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.photo_albums_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "photo_albums_visibility",
            ]
        )

        access = get_gallery_access_context(
            viewer=AnonymousUser(),
            target=owner,
        )

        assert access["can_view_profile"] is True
        assert access["can_view_gallery"] is False

    def test_owner_can_access_own_private_gallery(
        self,
        owner,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.photo_albums_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "photo_albums_visibility",
            ]
        )

        access = get_gallery_access_context(
            viewer=owner,
            target=owner,
        )

        assert access["can_view_profile"] is True
        assert access["can_view_gallery"] is True


@pytest.mark.django_db
class TestRealBlockIntegration:
    def test_owner_blocking_viewer_hides_profile(
        self,
        rf,
        owner,
        stranger,
    ):
        UserBlock.objects.create(
            blocker=owner,
            blocked=stranger,
        )

        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "profile_visibility",
            ]
        )

        request = rf.get("/")
        request.user = stranger

        with pytest.raises(Http404):
            ProfileContextBuilder.build_profile(
                request,
                owner.pk,
            )

    def test_viewer_blocking_owner_keeps_profile_but_closes_interactions(
        self,
        rf,
        owner,
        stranger,
    ):
        UserBlock.objects.create(
            blocker=stranger,
            blocked=owner,
        )

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

        request = rf.get("/")
        request.user = stranger

        context = ProfileContextBuilder.build_profile(
            request,
            owner.pk,
        )

        assert context["is_blocked"] is True
        assert context["viewer_has_blocked"] is True
        assert context["target_has_blocked"] is False

        assert context["access"]["can_view_profile"] is True
        assert context["access"]["can_view_friends"] is False
        assert context["access"]["can_send_message"] is False
        assert context["access"]["can_view_wall"] is False
        assert context["access"]["can_post_on_wall"] is False


@pytest.mark.django_db
class TestFailClosed:
    def test_unknown_profile_access_level_is_denied(
        self,
        owner,
        stranger,
    ):
        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
        )

        assert (
            access._check_access(
                "unsupported-access-level",
            )
            is False
        )

    def test_unknown_friends_access_level_is_denied(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=["profile_visibility"],
        )

        owner.settings.friends_visibility = "unsupported-access-level"

        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
        )

        assert access.can_view_friends() is False
