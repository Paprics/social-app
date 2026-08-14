# src/users/tests/profile/test_blocked_profile_view.py
"""HTTP behavior for profiles hidden by a user block."""

import pytest
from django.urls import reverse

from users.models.user_block import UserBlock


@pytest.mark.django_db
def test_profile_returns_notice_when_target_blocked_viewer(
    client,
    owner,
    stranger,
):
    UserBlock.objects.create(
        blocker=owner,
        blocked=stranger,
    )

    client.force_login(stranger)

    response = client.get(
        reverse(
            "users:profile",
            kwargs={"pk": owner.pk},
        )
    )

    assert response.status_code == 200
    assert response.context["target_has_blocked"] is True


@pytest.mark.django_db
def test_missing_profile_still_returns_404(
    client,
    owner,
):
    client.force_login(owner)

    response = client.get(
        reverse(
            "users:profile",
            kwargs={"pk": 999_999_999},
        )
    )

    assert response.status_code == 404
