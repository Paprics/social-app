# src/users/tests/user_block/test_selectors.py
"""Tests for user block selectors."""

import pytest

from users.models.user_block import UserBlock
from users.selectors.user_block import (
    get_blocked_count,
    get_blocked_relations,
    get_blockers_count,
    get_block_state,
    get_user_block_counts,
    has_blocked,
    is_blocked_between,
)


@pytest.mark.django_db
def test_directional_block_state(user_a, user_b):
    UserBlock.objects.create(
        blocker=user_a,
        blocked=user_b,
    )

    assert is_blocked_between(user_a, user_b) is True
    assert is_blocked_between(user_b, user_a) is True

    assert has_blocked(user_a, user_b) is True
    assert has_blocked(user_b, user_a) is False

    assert get_block_state(user_a, user_b) == {
        "is_blocked": True,
        "viewer_has_blocked": True,
        "target_has_blocked": False,
    }

    assert get_block_state(user_b, user_a) == {
        "is_blocked": True,
        "viewer_has_blocked": False,
        "target_has_blocked": True,
    }


@pytest.mark.django_db
def test_blocked_relations_and_counts(user_a, user_b, user_c):
    UserBlock.objects.create(
        blocker=user_a,
        blocked=user_b,
    )
    UserBlock.objects.create(
        blocker=user_a,
        blocked=user_c,
    )
    UserBlock.objects.create(
        blocker=user_c,
        blocked=user_a,
    )

    relations = list(
        get_blocked_relations(user_a),
    )

    assert {relation.blocked_id for relation in relations} == {
        user_b.pk,
        user_c.pk,
    }

    assert get_blocked_count(user_a) == 2
    assert get_blockers_count(user_a) == 1
    assert get_user_block_counts(user_a) == {
        "blocked": 2,
        "blockers": 1,
    }
