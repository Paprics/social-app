# src/gallery/tests/test_gallery_access.py

"""Tests for gallery access rules."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings

from gallery.services.access import GalleryAccessService


@pytest.mark.django_db
@override_settings(GALLERY_ALLOW_ANONYMOUS_VIEW=False)
def test_anonymous_gallery_access_is_disabled_by_setting(gallery_owner):
    """Anonymous users cannot access public galleries when disabled."""
    access = GalleryAccessService(
        viewer=AnonymousUser(),
        target=gallery_owner,
    )

    assert access.can_view_gallery() is False


@pytest.mark.django_db
@override_settings(GALLERY_ALLOW_ANONYMOUS_VIEW=True)
def test_anonymous_can_access_public_gallery_when_enabled(gallery_owner):
    """Anonymous users can access public galleries when enabled."""
    access = GalleryAccessService(
        viewer=AnonymousUser(),
        target=gallery_owner,
    )

    assert access.can_view_gallery() is True
