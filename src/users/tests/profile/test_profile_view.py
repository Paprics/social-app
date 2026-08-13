# src/users/tests/profile/test_profile_view.py

from unittest.mock import Mock

import pytest
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from users.views.profile import ProfileView


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.django_db
class TestProfileView:
    def test_view_builds_profile_context_and_renders_template(
        self,
        request_factory,
        owner,
        monkeypatch,
    ):
        request = request_factory.get("/")
        request.user = owner

        expected_context = {
            "target_user": owner,
            "is_owner": True,
        }

        build_profile_mock = Mock(
            return_value=expected_context,
        )

        render_mock = Mock(
            return_value=HttpResponse(status=200),
        )

        monkeypatch.setattr(
            "users.views.profile.ProfileContextBuilder.build_profile",
            build_profile_mock,
        )

        monkeypatch.setattr(
            "users.views.profile.render",
            render_mock,
        )

        response = ProfileView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        build_profile_mock.assert_called_once_with(
            request,
            owner.pk,
        )

        render_mock.assert_called_once_with(
            request,
            "users/profile.html",
            expected_context,
        )

    def test_view_passes_requested_pk_to_context_builder(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        request = request_factory.get("/")
        request.user = stranger

        build_profile_mock = Mock(
            return_value={
                "target_user": owner,
            }
        )

        monkeypatch.setattr(
            "users.views.profile.ProfileContextBuilder.build_profile",
            build_profile_mock,
        )

        monkeypatch.setattr(
            "users.views.profile.render",
            Mock(return_value=HttpResponse(status=200)),
        )

        ProfileView.as_view()(
            request,
            pk=owner.pk,
        )

        build_profile_mock.assert_called_once_with(
            request,
            owner.pk,
        )

    def test_404_from_context_builder_is_not_swallowed(
        self,
        request_factory,
        stranger,
        monkeypatch,
    ):
        request = request_factory.get("/")
        request.user = stranger

        monkeypatch.setattr(
            "users.views.profile.ProfileContextBuilder.build_profile",
            Mock(side_effect=Http404),
        )

        with pytest.raises(Http404):
            ProfileView.as_view()(
                request,
                pk=999999999,
            )
