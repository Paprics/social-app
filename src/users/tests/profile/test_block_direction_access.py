# src/users/tests/profile/test_block_direction_access.py
"""Regression tests for directional profile access after user blocking."""

import pytest
from django.urls import reverse

from users.models.friendship import Friendship
from users.models.preferences import UserSettings
from users.models.user_block import UserBlock
from users.services.profile_context import ProfileContextBuilder
from gallery.models import UserAlbum
from gallery.selectors.gallery import get_gallery_access_context


def _open_profile_settings(user):
    """Make profile resources public so block direction is the only variable."""

    user.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
    user.settings.friends_visibility = UserSettings.AccessLevel.EVERYONE
    user.settings.wall_enabled = True
    user.settings.wall_post_permission = UserSettings.AccessLevel.EVERYONE
    user.settings.photo_albums_visibility = UserSettings.AccessLevel.EVERYONE
    user.settings.save(
        update_fields=[
            "profile_visibility",
            "friends_visibility",
            "wall_enabled",
            "wall_post_permission",
            "photo_albums_visibility",
        ]
    )


@pytest.mark.django_db
def test_viewer_blocking_target_does_not_reduce_target_profile_access(
    rf,
    owner,
    stranger,
):
    """Viewer blocking target must not reduce viewer access to target profile."""

    _open_profile_settings(owner)

    UserBlock.objects.create(
        blocker=stranger,
        blocked=owner,
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
    assert context["access"]["can_view_friends"] is True
    assert context["access"]["can_view_wall"] is True
    assert context["access"]["can_post_on_wall"] is True


@pytest.mark.django_db
def test_viewer_blocking_target_keeps_normal_profile_page_wall_and_post_form(
    client,
    owner,
    stranger,
):
    """Blocking target must not strip target profile for the blocker."""

    _open_profile_settings(owner)

    UserBlock.objects.create(
        blocker=stranger,
        blocked=owner,
    )

    client.force_login(stranger)

    response = client.get(
        reverse(
            "users:profile",
            kwargs={"pk": owner.pk},
        )
    )

    assert response.status_code == 200

    assert response.context["viewer_has_blocked"] is True
    assert response.context["target_has_blocked"] is False

    assert response.context["access"]["can_view_profile"] is True
    assert response.context["access"]["can_view_friends"] is True
    assert response.context["access"]["can_view_wall"] is True
    assert response.context["access"]["can_post_on_wall"] is True

    rendered_templates = {template.name for template in response.templates if template.name}

    assert "users/profile.html" in rendered_templates
    assert "users/profile_blocked.html" not in rendered_templates
    assert "users/profile/_wall_post_form.html" in rendered_templates
    assert "users/profile/_wall.html" in rendered_templates


@pytest.mark.django_db
def test_target_blocking_viewer_keeps_reverse_direction_restricted(
    client,
    owner,
    stranger,
):
    """The blocked user must still receive the blocked-profile page."""

    _open_profile_settings(owner)

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
    assert response.context["viewer_has_blocked"] is False
    assert response.context["target_has_blocked"] is True

    rendered_templates = {template.name for template in response.templates if template.name}

    assert "users/profile_blocked.html" in rendered_templates
    assert "users/profile/_wall_post_form.html" not in rendered_templates
    assert "users/profile/_wall.html" not in rendered_templates


@pytest.mark.django_db
def test_viewer_blocking_target_keeps_friends_and_mutual_friends_visible(
    client,
    owner,
    stranger,
    friend,
    mutual,
):
    """Blocking target must not hide target friends or mutual friends."""

    _open_profile_settings(owner)

    Friendship.objects.create(
        from_user=owner,
        to_user=friend,
        status=Friendship.Status.ACCEPTED,
    )

    Friendship.objects.create(
        from_user=owner,
        to_user=mutual,
        status=Friendship.Status.ACCEPTED,
    )

    Friendship.objects.create(
        from_user=stranger,
        to_user=mutual,
        status=Friendship.Status.ACCEPTED,
    )

    UserBlock.objects.create(
        blocker=stranger,
        blocked=owner,
    )

    client.force_login(stranger)

    response = client.get(
        reverse(
            "users:profile",
            kwargs={"pk": owner.pk},
        )
    )

    assert response.status_code == 200

    assert response.context["viewer_has_blocked"] is True
    assert response.context["target_has_blocked"] is False
    assert response.context["access"]["can_view_profile"] is True
    assert response.context["access"]["can_view_friends"] is True

    friend_ids = {user.pk for user in response.context["friends"]}
    mutual_friend_ids = {user.pk for user in response.context["mutual_friends"]}

    assert friend.pk in friend_ids
    assert mutual.pk in friend_ids
    assert mutual.pk in mutual_friend_ids

    assert response.context["friends_count"] == 2
    assert response.context["mutual_friends_count"] == 1

    html = response.content.decode()

    assert friend.username in html
    assert mutual.username in html
    assert "Mutual friends" in html


@pytest.mark.django_db
def test_viewer_blocking_target_keeps_mutual_friends_visible(
    client,
    owner,
    stranger,
    mutual,
):
    """Blocking target must not hide mutual friends."""

    _open_profile_settings(owner)

    Friendship.objects.create(
        from_user=owner,
        to_user=mutual,
        status=Friendship.Status.ACCEPTED,
    )

    Friendship.objects.create(
        from_user=stranger,
        to_user=mutual,
        status=Friendship.Status.ACCEPTED,
    )

    UserBlock.objects.create(
        blocker=stranger,
        blocked=owner,
    )

    client.force_login(stranger)

    response = client.get(
        reverse(
            "users:profile",
            kwargs={"pk": owner.pk},
        )
    )

    assert response.status_code == 200
    assert response.context["viewer_has_blocked"] is True
    assert response.context["target_has_blocked"] is False
    assert response.context["access"]["can_view_friends"] is True

    mutual_friend_ids = {user.pk for user in response.context["mutual_friends"]}

    assert mutual.pk in mutual_friend_ids
    assert response.context["mutual_friends_count"] == 1


@pytest.mark.django_db
def test_viewer_blocking_target_keeps_public_albums_visible(
    client,
    owner,
    stranger,
):
    """Blocking target must not hide target public albums."""

    _open_profile_settings(owner)

    album = UserAlbum.objects.create(
        user=owner,
        title="Visible album",
        album_type=UserAlbum.AlbumType.PHOTO,
        purpose=UserAlbum.Purpose.USER,
        visibility=UserAlbum.Visibility.PUBLIC,
        is_visible=True,
    )

    UserBlock.objects.create(
        blocker=stranger,
        blocked=owner,
    )

    client.force_login(stranger)

    response = client.get(
        reverse(
            "users:profile",
            kwargs={"pk": owner.pk},
        )
    )

    assert response.status_code == 200
    assert response.context["viewer_has_blocked"] is True
    assert response.context["target_has_blocked"] is False
    assert response.context["access"]["can_view_profile"] is True

    album_ids = {item.pk for item in response.context["albums"]}

    assert album.pk in album_ids
    assert response.context["albums_count"] == 1


@pytest.mark.django_db
def test_viewer_blocking_target_does_not_close_gallery_access(
    owner,
    stranger,
):
    _open_profile_settings(owner)

    UserBlock.objects.create(
        blocker=stranger,
        blocked=owner,
    )

    access = get_gallery_access_context(
        viewer=stranger,
        target=owner,
    )

    assert access["can_view_profile"] is True
    assert access["can_view_gallery"] is True
