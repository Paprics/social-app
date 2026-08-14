# src/users/tests/friendship/test_selectors.py
"""Tests for read-only friendship selectors and mutual-friend queries."""

import pytest
from django.utils import timezone

from users.models.friendship import Friendship
from users.selectors.friendship import (
    get_friends,
    get_friends_count,
    get_friends_preview,
    get_incoming_requests,
    get_incoming_requests_count,
    get_mutual_friends,
    get_mutual_friends_count,
    get_outgoing_requests,
    get_outgoing_requests_count,
    get_friendship_counts,
)


def create_friendship(from_user, to_user, *, accepted=True):
    return Friendship.objects.create(
        from_user=from_user,
        to_user=to_user,
        status=(Friendship.Status.ACCEPTED if accepted else Friendship.Status.PENDING),
        accepted_at=timezone.now() if accepted else None,
    )


@pytest.mark.django_db
class TestFriendSelectors:
    def test_get_friends_returns_accepted_relations_in_both_directions(
        self,
        user_a,
        user_b,
        user_c,
    ):
        first = create_friendship(user_a, user_b)
        second = create_friendship(user_c, user_a)

        result = list(get_friends(user_a))

        assert set(result) == {
            first,
            second,
        }

    def test_pending_request_is_not_returned_as_friend(
        self,
        pending_friend_request,
        user_a,
    ):
        assert list(get_friends(user_a)) == []

    def test_unrelated_friendships_are_not_returned(
        self,
        user_a,
        user_b,
        user_c,
        user_d,
    ):
        create_friendship(user_c, user_d)

        assert list(get_friends(user_a)) == []

    def test_friends_count_counts_only_accepted(
        self,
        user_a,
        user_b,
        user_c,
    ):
        create_friendship(user_a, user_b)
        create_friendship(
            user_a,
            user_c,
            accepted=False,
        )

        assert get_friends_count(user_a) == 1


@pytest.mark.django_db
class TestRequestSelectors:
    def test_incoming_requests_return_only_received_pending(
        self,
        user_a,
        user_b,
        user_c,
    ):
        incoming = create_friendship(
            user_b,
            user_a,
            accepted=False,
        )

        create_friendship(
            user_a,
            user_c,
            accepted=False,
        )

        assert list(get_incoming_requests(user_a)) == [incoming]

    def test_outgoing_requests_return_only_sent_pending(
        self,
        user_a,
        user_b,
        user_c,
    ):
        outgoing = create_friendship(
            user_a,
            user_b,
            accepted=False,
        )

        create_friendship(
            user_c,
            user_a,
            accepted=False,
        )

        assert list(get_outgoing_requests(user_a)) == [outgoing]

    def test_request_counts(self, user_a, user_b, user_c):
        create_friendship(
            user_b,
            user_a,
            accepted=False,
        )
        create_friendship(
            user_a,
            user_c,
            accepted=False,
        )

        assert get_incoming_requests_count(user_a) == 1
        assert get_outgoing_requests_count(user_a) == 1


@pytest.mark.django_db
class TestMutualFriends:
    def test_mutual_friend_is_detected_regardless_of_direction(
        self,
        user_a,
        user_b,
        user_c,
    ):
        create_friendship(user_a, user_c)
        create_friendship(user_c, user_b)

        assert list(
            get_mutual_friends(
                user_a,
                user_b,
            )
        ) == [user_c]

    def test_multiple_mutual_friends_with_mixed_directions(
        self,
        user_a,
        user_b,
        user_c,
        user_d,
    ):
        create_friendship(user_a, user_c)
        create_friendship(user_c, user_b)

        create_friendship(user_d, user_a)
        create_friendship(user_b, user_d)

        result = set(
            get_mutual_friends(
                user_a,
                user_b,
            )
        )

        assert result == {
            user_c,
            user_d,
        }

        assert (
            get_mutual_friends_count(
                user_a,
                user_b,
            )
            == 2
        )

    def test_pending_relation_is_not_mutual_friend(
        self,
        user_a,
        user_b,
        user_c,
    ):
        create_friendship(user_a, user_c)

        create_friendship(
            user_c,
            user_b,
            accepted=False,
        )

        assert (
            list(
                get_mutual_friends(
                    user_a,
                    user_b,
                )
            )
            == []
        )


@pytest.mark.django_db
class TestFriendsPreview:
    def test_preview_respects_limit(
        self,
        friendship_user_factory,
        user_a,
    ):
        friends = []

        for index in range(6):
            friend = friendship_user_factory(f"preview_friend_{index}")
            friends.append(friend)
            create_friendship(user_a, friend)

        result = get_friends_preview(
            user_a,
            limit=3,
        )

        assert len(result) == 3
        assert set(result).issubset(set(friends))

    def test_preview_excludes_pending_requests(
        self,
        user_a,
        user_b,
    ):
        create_friendship(
            user_a,
            user_b,
            accepted=False,
        )

        assert get_friends_preview(user_a) == []


@pytest.mark.django_db
def test_friendship_counts(user_a, user_b, user_c, user_d):
    create_friendship(
        user_a,
        user_b,
        accepted=True,
    )

    create_friendship(
        user_c,
        user_a,
        accepted=False,
    )

    create_friendship(
        user_a,
        user_d,
        accepted=False,
    )

    assert get_friendship_counts(user_a) == {
        "friends": 1,
        "incoming": 1,
        "outgoing": 1,
    }
