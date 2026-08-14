# src/users/tests/user_block/test_account_center.py
"""Tests for Account Center blacklist behavior."""

import pytest
from django.urls import reverse

from users.models.user_block import UserBlock


@pytest.mark.django_db
def test_blacklist_list_contains_only_blocks_created_by_current_user(
    client,
    user_a,
    user_b,
    user_c,
):
    UserBlock.objects.create(
        blocker=user_a,
        blocked=user_b,
    )
    UserBlock.objects.create(
        blocker=user_c,
        blocked=user_a,
    )

    client.force_login(user_a)

    response = client.get(
        reverse("users:account_center_blacklist_list"),
    )

    assert response.status_code == 200

    blocks = list(response.context["blocks"])

    assert [block.blocked_id for block in blocks] == [
        user_b.pk,
    ]

    assert response.context["block_counts"] == {
        "blocked": 1,
        "blockers": 1,
    }


@pytest.mark.django_db
def test_account_center_unblock_removes_block_and_triggers_refresh(
    client,
    user_a,
    user_b,
):
    UserBlock.objects.create(
        blocker=user_a,
        blocked=user_b,
    )

    client.force_login(user_a)

    response = client.post(
        reverse(
            "users:unblock",
            kwargs={"pk": user_b.pk},
        )
        + "?context=account_center"
    )

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == "blockChanged"

    assert not UserBlock.objects.filter(
        blocker=user_a,
        blocked=user_b,
    ).exists()


@pytest.mark.django_db
def test_account_center_shell_contains_block_counts(
    client,
    user_a,
    user_b,
    user_c,
):
    UserBlock.objects.create(
        blocker=user_a,
        blocked=user_b,
    )
    UserBlock.objects.create(
        blocker=user_c,
        blocked=user_a,
    )

    client.force_login(user_a)

    response = client.get(
        reverse("users:account_center"),
    )

    assert response.status_code == 200
    assert response.context["block_counts"] == {
        "blocked": 1,
        "blockers": 1,
    }
