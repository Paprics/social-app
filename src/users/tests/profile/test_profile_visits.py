# src/users/tests/profile/test_profile_visits.py

from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser
from redis.exceptions import RedisError

from users.services.profile_context import ProfileContextBuilder
from users.services.profile_visits import ProfileVisitService


@pytest.mark.django_db
class TestProfileContextVisits:
    def test_authenticated_user_visit_is_recorded(
        self,
        owner,
        stranger,
        monkeypatch,
    ):
        record_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_context.ProfileVisitService.record",
            record_mock,
        )

        ProfileContextBuilder._record_visit(
            viewer=stranger,
            target=owner,
        )

        record_mock.assert_called_once_with(
            stranger.pk,
            owner.pk,
        )

    def test_anonymous_visit_is_not_recorded(
        self,
        owner,
        monkeypatch,
    ):
        record_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_context.ProfileVisitService.record",
            record_mock,
        )

        ProfileContextBuilder._record_visit(
            viewer=AnonymousUser(),
            target=owner,
        )

        record_mock.assert_not_called()

    def test_owner_visit_is_not_recorded(
        self,
        owner,
        monkeypatch,
    ):
        record_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_context.ProfileVisitService.record",
            record_mock,
        )

        ProfileContextBuilder._record_visit(
            viewer=owner,
            target=owner,
        )

        record_mock.assert_not_called()


class TestProfileVisitService:
    def test_self_visit_is_ignored(
        self,
        monkeypatch,
    ):
        cache_add_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_visits.cache.add",
            cache_add_mock,
        )

        ProfileVisitService.record(
            visitor_id=10,
            target_id=10,
        )

        cache_add_mock.assert_not_called()

    def test_visit_is_queued_when_lock_is_created(
        self,
        monkeypatch,
    ):
        redis_mock = Mock()

        cache_mock = Mock()
        cache_mock.add.return_value = True
        cache_mock.client.get_client.return_value = redis_mock

        monkeypatch.setattr(
            "users.services.profile_visits.cache",
            cache_mock,
        )

        ProfileVisitService.record(
            visitor_id=10,
            target_id=20,
        )

        cache_mock.add.assert_called_once_with(
            "profile_visit_lock:10:20",
            True,
            timeout=ProfileVisitService.LOCK_TIMEOUT,
        )

        cache_mock.client.get_client.assert_called_once_with(
            write=True,
        )

        redis_mock.sadd.assert_called_once_with(
            ProfileVisitService.PENDING_KEY,
            "10:20",
        )

    def test_duplicate_visit_within_lock_period_is_ignored(
        self,
        monkeypatch,
    ):
        cache_mock = Mock()
        cache_mock.add.return_value = False

        monkeypatch.setattr(
            "users.services.profile_visits.cache",
            cache_mock,
        )

        ProfileVisitService.record(
            visitor_id=10,
            target_id=20,
        )

        cache_mock.add.assert_called_once_with(
            "profile_visit_lock:10:20",
            True,
            timeout=ProfileVisitService.LOCK_TIMEOUT,
        )

        cache_mock.client.get_client.assert_not_called()

    def test_redis_failure_does_not_escape_service(
        self,
        monkeypatch,
    ):
        cache_mock = Mock()
        cache_mock.add.side_effect = RedisError("Redis unavailable")

        monkeypatch.setattr(
            "users.services.profile_visits.cache",
            cache_mock,
        )

        ProfileVisitService.record(
            visitor_id=10,
            target_id=20,
        )

        cache_mock.add.assert_called_once()
