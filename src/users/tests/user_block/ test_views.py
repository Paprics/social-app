# src/users/tests/user_block/test_views.py
"""HTTP tests for block and unblock actions."""

import pytest
from django.urls import reverse

from users.models.user_block import UserBlock


@pytest.mark.django_db
def test_block_view_creates_relation(client, user_a, user_b):
    client.force_login(user_a)

    response = client.post(
        reverse(
            "users:block",
            kwargs={"pk": user_b.pk},
        )
    )

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == "blockChanged"

    assert UserBlock.objects.filter(
        blocker=user_a,
        blocked=user_b,
    ).exists()


@pytest.mark.django_db
def test_unblock_view_removes_relation(client, user_a, user_b):
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
    )

    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == "blockChanged"

    assert not UserBlock.objects.filter(
        blocker=user_a,
        blocked=user_b,
    ).exists()
