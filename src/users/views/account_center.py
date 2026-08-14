# src/users/views/account_center.py
"""Account Center pages and paginated user relationship sections."""

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import ListView, TemplateView

from users.models import ProfileVisit
from users.selectors.friendship import (
    get_friends,
    get_friends_count,
    get_friendship_counts,
    get_incoming_requests,
    get_outgoing_requests,
)
from users.selectors.user_block import (
    get_blocked_relations,
    get_blockers_count,
    get_user_block_counts,
)


class AccountCenterProfileVisitsView(LoginRequiredMixin, ListView):
    """Display paginated profile visits."""

    template_name = "users/partials/account_center/profile_visits_list.html"
    context_object_name = "visits"
    paginate_by = 5

    def get_queryset(self):
        return (
            ProfileVisit.objects.filter(
                profile=self.request.user,
            )
            .select_related(
                "visitor",
                "visitor__profile",
            )
            .order_by("-visited_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_premium"] = self.request.user.profile.is_premium if hasattr(self.request.user, "profile") else False

        return context


class AccountCenterStatisticsView(LoginRequiredMixin, TemplateView):
    """Display account statistics."""

    template_name = "users/partials/account_center/statistics_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        context |= {
            "registration_date": user.date_joined,
            "friends_count": get_friends_count(user),
            "profile_views": 0,
            "favorites_count": 13,
            "gifts_received": 0,
            "blockers_count": get_blockers_count(user),
        }

        return context


class AccountCenterFriendshipListView(LoginRequiredMixin, ListView):
    """Base view for paginated friendship sections in Account Center."""

    paginate_by = settings.ACCOUNT_CENTER_FRIENDSHIP_PAGE_SIZE
    friendship_count_key = None
    pagination_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        counts = get_friendship_counts(
            self.request.user,
        )

        context["friendship_counts"] = counts

        if self.friendship_count_key is not None:
            context["total_count"] = counts[self.friendship_count_key]

        if self.pagination_url_name is not None:
            context["pagination_url"] = reverse(
                self.pagination_url_name,
            )

        return context


class AccountCenterFriendsListView(AccountCenterFriendshipListView):
    """Display accepted friendships."""

    template_name = "users/partials/account_center/friends_list_tab.html"
    context_object_name = "friendships"
    friendship_count_key = "friends"
    pagination_url_name = "users:account_center_friends_list"

    def get_queryset(self):
        return get_friends(
            self.request.user,
        )


class AccountCenterOutgoingFriendRequestsView(AccountCenterFriendshipListView):
    """Display pending friend requests sent by the current user."""

    template_name = "users/partials/account_center/outgoing_requests_tab.html"
    context_object_name = "friend_requests"
    friendship_count_key = "outgoing"
    pagination_url_name = "users:account_center_friends_outgoing"

    def get_queryset(self):
        return get_outgoing_requests(
            self.request.user,
        )


class AccountCenterIncomingFriendRequestsView(AccountCenterFriendshipListView):
    """Display pending friend requests received by the current user."""

    template_name = "users/partials/account_center/incoming_requests_tab.html"
    context_object_name = "friend_requests"
    friendship_count_key = "incoming"
    pagination_url_name = "users:account_center_friends_incoming"

    def get_queryset(self):
        return get_incoming_requests(
            self.request.user,
        )


class AccountCenterBlacklistListView(LoginRequiredMixin, ListView):
    """Display users blocked by the current user."""

    template_name = "users/partials/account_center/blacklist_list.html"
    context_object_name = "blocks"
    paginate_by = settings.ACCOUNT_CENTER_BLACKLIST_PAGE_SIZE

    def get_queryset(self):
        return get_blocked_relations(
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["block_counts"] = get_user_block_counts(
            self.request.user,
        )
        context["pagination_url"] = reverse(
            "users:account_center_blacklist_list",
        )

        return context


class AccountCenterView(LoginRequiredMixin, TemplateView):
    """Display the Account Center shell."""

    template_name = "users/account_center.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["friendship_counts"] = get_friendship_counts(
            self.request.user,
        )
        context["block_counts"] = get_user_block_counts(
            self.request.user,
        )

        return context
