# src/users/tests/user_block/conftest.py
"""Fixtures for user blocking tests."""

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from users.models.profile import Profile

User = get_user_model()

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def block_user_factory(db):
    """Create users with profiles required by block views."""

    counter = itertools.count(1)

    def create_user(username=None):
        number = next(counter)

        user = User.objects.create_user(
            username=username or f"block_test_user_{number}",
            password=TEST_PASSWORD,
        )

        Profile.objects.create(
            user=user,
            birth_date=date(1990, 1, 1),
            gender=Profile.Gender.MALE,
        )

        return user

    return create_user


@pytest.fixture
def user_a(block_user_factory):
    return block_user_factory("block_user_a")


@pytest.fixture
def user_b(block_user_factory):
    return block_user_factory("block_user_b")


@pytest.fixture
def user_c(block_user_factory):
    return block_user_factory("block_user_c")
