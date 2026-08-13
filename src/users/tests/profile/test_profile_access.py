# src/users/tests/profile/test_profile_access.py

import pytest
from django.contrib.auth.models import AnonymousUser

from users.models.preferences import UserSettings
from users.services.access import ProfileAccessService


@pytest.mark.django_db
class TestProfileVisibility:
    @pytest.mark.parametrize(
        ("access_level", "is_friend", "expected"),
        [
            (UserSettings.AccessLevel.EVERYONE, False, True),
            (UserSettings.AccessLevel.EVERYONE, True, True),
            (UserSettings.AccessLevel.FRIENDS, False, False),
            (UserSettings.AccessLevel.FRIENDS, True, True),
            (UserSettings.AccessLevel.ONLY_ME, False, False),
            (UserSettings.AccessLevel.ONLY_ME, True, False),
        ],
    )
    def test_authenticated_access(
        self,
        owner,
        stranger,
        access_level,
        is_friend,
        expected,
    ):
        owner.settings.profile_visibility = access_level
        owner.settings.save(
            update_fields=["profile_visibility"],
        )

        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
            is_friend=is_friend,
        )

        assert access.can_view_profile() is expected

    def test_owner_always_has_access(self, owner):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(
            update_fields=["profile_visibility"],
        )

        access = ProfileAccessService(
            viewer=owner,
            target=owner,
        )

        assert access.can_view_profile() is True

    @pytest.mark.parametrize(
        ("access_level", "expected"),
        [
            (UserSettings.AccessLevel.EVERYONE, True),
            (UserSettings.AccessLevel.FRIENDS, False),
            (UserSettings.AccessLevel.ONLY_ME, False),
        ],
    )
    def test_anonymous_access(
        self,
        owner,
        access_level,
        expected,
    ):
        owner.settings.profile_visibility = access_level
        owner.settings.save(
            update_fields=["profile_visibility"],
        )

        access = ProfileAccessService(
            viewer=AnonymousUser(),
            target=owner,
        )

        assert access.can_view_profile() is expected


@pytest.mark.django_db
class TestFriendsVisibility:
    def test_public_friends_are_visible_when_profile_is_public(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
        )

        assert access.can_view_friends() is True

    def test_friends_are_hidden_when_profile_itself_is_private(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
        )

        assert access.can_view_friends() is False

    def test_friends_only_visibility_allows_friend(
        self,
        owner,
        friend,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.friends_visibility = UserSettings.AccessLevel.FRIENDS
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        access = ProfileAccessService(
            viewer=friend,
            target=owner,
            is_friend=True,
        )

        assert access.can_view_friends() is True

    def test_friends_only_visibility_denies_stranger(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.friends_visibility = UserSettings.AccessLevel.FRIENDS
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
            is_friend=False,
        )

        assert access.can_view_friends() is False

    def test_profile_friends_only_blocks_stranger_even_if_friends_list_is_public(
        self,
        owner,
        stranger,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.FRIENDS
        owner.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        access = ProfileAccessService(
            viewer=stranger,
            target=owner,
            is_friend=False,
        )

        assert access.can_view_friends() is False

    def test_owner_can_view_friends_with_only_me_settings(
        self,
        owner,
    ):
        owner.settings.profile_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.friends_visibility = UserSettings.AccessLevel.ONLY_ME
        owner.settings.save(
            update_fields=[
                "profile_visibility",
                "friends_visibility",
            ]
        )

        access = ProfileAccessService(
            viewer=owner,
            target=owner,
        )

        assert access.can_view_friends() is True

    @pytest.mark.django_db
    class TestFriendsAccessHierarchyMatrix:
        @pytest.mark.parametrize(
            (
                "profile_visibility",
                "friends_visibility",
                "is_friend",
                "expected",
            ),
            [
                # ---------------------------------------------------------
                # Profile: EVERYONE
                # ---------------------------------------------------------
                (
                    UserSettings.AccessLevel.EVERYONE,
                    UserSettings.AccessLevel.EVERYONE,
                    False,
                    True,
                ),
                (
                    UserSettings.AccessLevel.EVERYONE,
                    UserSettings.AccessLevel.EVERYONE,
                    True,
                    True,
                ),
                (
                    UserSettings.AccessLevel.EVERYONE,
                    UserSettings.AccessLevel.FRIENDS,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.EVERYONE,
                    UserSettings.AccessLevel.FRIENDS,
                    True,
                    True,
                ),
                (
                    UserSettings.AccessLevel.EVERYONE,
                    UserSettings.AccessLevel.ONLY_ME,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.EVERYONE,
                    UserSettings.AccessLevel.ONLY_ME,
                    True,
                    False,
                ),
                # ---------------------------------------------------------
                # Profile: FRIENDS
                # ---------------------------------------------------------
                (
                    UserSettings.AccessLevel.FRIENDS,
                    UserSettings.AccessLevel.EVERYONE,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.FRIENDS,
                    UserSettings.AccessLevel.EVERYONE,
                    True,
                    True,
                ),
                (
                    UserSettings.AccessLevel.FRIENDS,
                    UserSettings.AccessLevel.FRIENDS,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.FRIENDS,
                    UserSettings.AccessLevel.FRIENDS,
                    True,
                    True,
                ),
                (
                    UserSettings.AccessLevel.FRIENDS,
                    UserSettings.AccessLevel.ONLY_ME,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.FRIENDS,
                    UserSettings.AccessLevel.ONLY_ME,
                    True,
                    False,
                ),
                # ---------------------------------------------------------
                # Profile: ONLY_ME
                # ---------------------------------------------------------
                (
                    UserSettings.AccessLevel.ONLY_ME,
                    UserSettings.AccessLevel.EVERYONE,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.ONLY_ME,
                    UserSettings.AccessLevel.EVERYONE,
                    True,
                    False,
                ),
                (
                    UserSettings.AccessLevel.ONLY_ME,
                    UserSettings.AccessLevel.FRIENDS,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.ONLY_ME,
                    UserSettings.AccessLevel.FRIENDS,
                    True,
                    False,
                ),
                (
                    UserSettings.AccessLevel.ONLY_ME,
                    UserSettings.AccessLevel.ONLY_ME,
                    False,
                    False,
                ),
                (
                    UserSettings.AccessLevel.ONLY_ME,
                    UserSettings.AccessLevel.ONLY_ME,
                    True,
                    False,
                ),
            ],
        )
        def test_friends_access_hierarchy(
            self,
            owner,
            stranger,
            profile_visibility,
            friends_visibility,
            is_friend,
            expected,
        ):
            owner.settings.profile_visibility = profile_visibility
            owner.settings.friends_visibility = friends_visibility
            owner.settings.save(
                update_fields=[
                    "profile_visibility",
                    "friends_visibility",
                ]
            )

            access = ProfileAccessService(
                viewer=stranger,
                target=owner,
                is_friend=is_friend,
            )

            assert access.can_view_friends() is expected

    @pytest.mark.django_db
    class TestProfileAccessDefensiveFallback:
        def test_unknown_profile_access_level_is_denied(
            self,
            owner,
            stranger,
        ):
            access = ProfileAccessService(
                viewer=stranger,
                target=owner,
            )

            assert access._check_access("unknown-access-level") is False

        def test_unknown_friends_access_level_is_denied(
            self,
            owner,
            stranger,
            monkeypatch,
        ):
            owner.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
            owner.settings.save(
                update_fields=["profile_visibility"],
            )

            monkeypatch.setattr(
                owner.settings,
                "friends_visibility",
                "unknown-access-level",
            )

            access = ProfileAccessService(
                viewer=stranger,
                target=owner,
            )

            assert access.can_view_friends() is False
