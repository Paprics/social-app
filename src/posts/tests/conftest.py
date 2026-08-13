# src/posts/tests/conftest.py

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from posts.models import Comment, Post
from users.models.profile import Profile

User = get_user_model()

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def user_factory(db):
    """Create a complete user suitable for posts tests."""

    counter = itertools.count(1)

    def create_user(username=None):
        number = next(counter)

        user = User.objects.create_user(
            username=username or f"test_user_{number}",
            password=TEST_PASSWORD,
        )

        # UserSettings is created by the project's user signal.
        assert hasattr(user, "settings")

        # Profile is not created by User.objects.create_user(),
        # so tests create it explicitly.
        Profile.objects.create(
            user=user,
            birth_date=date(1990, 1, 1),
            gender=Profile.Gender.MALE,
        )

        assert hasattr(user, "profile")

        return user

    return create_user


@pytest.fixture
def owner(user_factory):
    """Owner of the wall."""

    return user_factory("wall_owner")


@pytest.fixture
def author(user_factory):
    """User who publishes content on another user's wall."""

    return user_factory("post_author")


@pytest.fixture
def other(user_factory):
    """Unrelated authenticated user."""

    return user_factory("other_user")


@pytest.fixture
def wall_post(owner, author):
    """Post written by author on owner's wall."""

    return Post.objects.create(
        owner=owner,
        author=author,
        content="Initial post content",
    )


@pytest.fixture
def comment(wall_post, other):
    """Comment written by other user under wall_post."""

    return Comment.objects.create(
        post=wall_post,
        author=other,
        content="Initial comment",
    )


@pytest.fixture
def staff_user(user_factory):
    """User allowed to use post image attachments."""

    user = user_factory("staff_user")
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    return user
