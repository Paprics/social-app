# src/users/tests/profile/conftest.py

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from users.models.friendship import Friendship
from users.models.preferences import UserSettings
from users.models.profile import Profile

User = get_user_model()

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def profile_user_factory(db):
    counter = itertools.count(1)

    def create_user(username=None):
        number = next(counter)

        user = User.objects.create_user(
            username=username or f"profile_test_user_{number}",
            password=TEST_PASSWORD,
        )

        assert hasattr(user, "settings")

        Profile.objects.create(
            user=user,
            birth_date=date(1990, 1, 1),
            gender=Profile.Gender.MALE,
        )

        return user

    return create_user


@pytest.fixture
def owner(profile_user_factory):
    return profile_user_factory("profile_owner")


@pytest.fixture
def stranger(profile_user_factory):
    return profile_user_factory("profile_stranger")


@pytest.fixture
def friend(profile_user_factory):
    return profile_user_factory("profile_friend")


@pytest.fixture
def mutual(profile_user_factory):
    return profile_user_factory("profile_mutual")


@pytest.fixture
def accepted_friendship(owner, friend):
    return Friendship.objects.create(
        from_user=owner,
        to_user=friend,
        status=Friendship.Status.ACCEPTED,
    )


@pytest.fixture
def public_owner(owner):
    settings = owner.settings

    settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
    settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
    settings.photo_albums_visibility = UserSettings.AccessLevel.EVERYONE
    settings.message_permission = UserSettings.AccessLevel.EVERYONE
    settings.comment_permission = UserSettings.AccessLevel.EVERYONE
    settings.wall_post_permission = UserSettings.AccessLevel.EVERYONE
    settings.wall_enabled = True
    settings.comments_enabled = True

    settings.save(
        update_fields=[
            "profile_visibility",
            "friends_visibility",
            "photo_albums_visibility",
            "message_permission",
            "comment_permission",
            "wall_post_permission",
            "wall_enabled",
            "comments_enabled",
        ]
    )

    return owner
