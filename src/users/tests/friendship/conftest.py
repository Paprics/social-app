# src/users/tests/friendship/conftest.py
"""Shared fixtures for friendship domain tests."""

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from users.models.friendship import Friendship
from users.models.profile import Profile

User = get_user_model()

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def friendship_user_factory(db):
    """Create complete users suitable for friendship tests."""

    counter = itertools.count(1)

    def create_user(username=None):
        number = next(counter)

        user = User.objects.create_user(
            username=username or f"friendship_user_{number}",
            password=TEST_PASSWORD,
        )

        Profile.objects.get_or_create(
            user=user,
            defaults={
                "birth_date": date(1990, 1, 1),
                "gender": Profile.Gender.MALE,
            },
        )

        return user

    return create_user


@pytest.fixture
def user_a(friendship_user_factory):
    return friendship_user_factory("friendship_a")


@pytest.fixture
def user_b(friendship_user_factory):
    return friendship_user_factory("friendship_b")


@pytest.fixture
def user_c(friendship_user_factory):
    return friendship_user_factory("friendship_c")


@pytest.fixture
def user_d(friendship_user_factory):
    return friendship_user_factory("friendship_d")


@pytest.fixture
def pending_friend_request(user_a, user_b):
    return Friendship.objects.create(
        from_user=user_a,
        to_user=user_b,
        status=Friendship.Status.PENDING,
    )


@pytest.fixture
def accepted_friendship(user_a, user_b):
    return Friendship.objects.create(
        from_user=user_a,
        to_user=user_b,
        status=Friendship.Status.ACCEPTED,
        accepted_at=timezone.now(),
    )
