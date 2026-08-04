from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import TemplateView, ListView
from users.models.friendship import Friendship
from users.services.friendship_service import FriendshipService
from users.models import ProfileVisit

User = get_user_model()


class AccountCenterProfileVisitsView(LoginRequiredMixin, ListView):
    template_name = "users/partials/account_center/profile_visits_list.html"
    context_object_name = "visits"
    paginate_by = 5

    def get_queryset(self):
        return (
            ProfileVisit.objects.filter(profile=self.request.user)
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
    template_name = "users/partials/account_center/statistics_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        context |= {
            "registration_date": user.date_joined,
            "friends_count": FriendshipService.get_friends_count(user),
            "profile_views": 0,
            "favorites_count": 13,
            "gifts_received": 0,
        }

        return context


class AccountCenterFriendsListView(LoginRequiredMixin, ListView):
    template_name = "users/partials/account_center/friends_list_tab.html"
    context_object_name = "friendships"
    paginate_by = 10

    def get_queryset(self):
        return FriendshipService.get_friends(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pagination_url"] = reverse("users:account_center_friends_list")
        return context


class AccountCenterOutgoingFriendRequestsView(LoginRequiredMixin, ListView):
    template_name = "users/partials/account_center/outgoing_requests_tab.html"
    context_object_name = "friend_requests"
    paginate_by = 10

    def get_queryset(self):
        return FriendshipService.get_outgoing_requests(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pagination_url"] = reverse("users:account_center_friends_outgoing")
        return context


class AccountCenterIncomingFriendRequestsView(LoginRequiredMixin, ListView):
    template_name = "users/partials/account_center/incoming_requests_tab.html"
    context_object_name = "friend_requests"
    paginate_by = 10

    def get_queryset(self):
        return FriendshipService.get_incoming_requests(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pagination_url"] = reverse("users:account_center_friends_incoming")
        return context


class AccountCenterView(LoginRequiredMixin, TemplateView):
    template_name = "users/account_center.html"
