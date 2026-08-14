# src/users/tests/friendship/test_model.py
"""Tests for Friendship model invariants and database constraints."""

import pytest
from django.db import IntegrityError, transaction

from users.models.friendship import Friendship


@pytest.mark.django_db
class TestFriendshipModel:
    def test_new_friendship_is_pending_by_default(self, user_a, user_b):
        friendship = Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        assert friendship.status == Friendship.Status.PENDING
        assert friendship.accepted_at is None

    def test_self_friendship_is_rejected_by_database(self, user_a):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    from_user=user_a,
                    to_user=user_a,
                )

    def test_reverse_duplicate_pair_is_rejected(self, user_a, user_b):
        Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    from_user=user_b,
                    to_user=user_a,
                )

    def test_same_direction_duplicate_pair_is_rejected(self, user_a, user_b):
        Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    from_user=user_a,
                    to_user=user_b,
                )

    def test_unknown_status_is_rejected_by_database(self, user_a, user_b):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    from_user=user_a,
                    to_user=user_b,
                    status="banana",
                )

    def test_deleting_user_deletes_friendship(self, user_a, user_b):
        friendship = Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        friendship_id = friendship.pk

        user_a.delete()

        assert not Friendship.objects.filter(pk=friendship_id).exists()

    def test_string_representation_contains_users_and_status(self, user_a, user_b):
        friendship = Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        value = str(friendship)

        assert str(user_a) in value
        assert str(user_b) in value
        assert friendship.get_status_display() in value
