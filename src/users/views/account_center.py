# src/users/views/account_center.py
"""Account Center pages and paginated user relationship sections."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import ListView, TemplateView
from gallery.models import Photo
from gallery.selectors.gallery import get_gallery_access_context
from gallery.selectors.photos import get_photo_for_view
from gallery.selectors.likes import get_user_liked_photos

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
from users.selectors.favorite import (
    get_favorite_photos,
    get_favorite_profiles,
    get_favorites_count,
    get_profile_favorites_count,
)

User = get_user_model()


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
            "favorites_count": get_favorites_count(user),
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


class AccountCenterFavoritePhotosView(LoginRequiredMixin, ListView):
    """Display paginated favorite photos."""

    template_name = "users/partials/account_center/favorite_photos_list.html"
    context_object_name = "favorite_relations"

    def get_paginate_by(self, queryset):
        return getattr(
            settings,
            "ACCOUNT_CENTER_FAVORITE_PHOTOS_PAGE_SIZE",
            12,
        )

    def get_queryset(self):
        return get_favorite_photos(
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        relations = list(
            context["favorite_relations"],
        )

        photo_ids = [relation.object_id for relation in relations]

        photos_by_id = (
            Photo.objects.filter(pk__in=photo_ids)
            .select_related(
                "album",
                "album__user",
                "album__user__profile",
                "album__user__settings",
            )
            .in_bulk()
        )

        photos = []

        for relation in relations:
            photo = photos_by_id.get(
                relation.object_id,
            )

            # Удалённая фотография → orphan Favorite.
            if photo is None:
                continue

            target = photo.album.user

            access = get_gallery_access_context(
                viewer=self.request.user,
                target=target,
            )

            if not access["can_view_profile"]:
                continue

            if not access["can_view_gallery"]:
                continue

            accessible_photo = get_photo_for_view(
                target=target,
                photo_id=photo.pk,
                access=access,
            )

            if accessible_photo is None:
                continue

            photos.append(
                accessible_photo,
            )

        context["photos"] = photos
        context["pagination_url"] = reverse(
            "users:account_center_favorite_photos",
        )
        context["pagination_target"] = "#fav-photos"

        return context


class AccountCenterLikedPhotosView(LoginRequiredMixin, ListView):
    """Display paginated photos liked by the current user."""

    template_name = "users/partials/account_center/liked_photos_list.html"
    context_object_name = "liked_photos"
    paginate_by = settings.ACCOUNT_CENTER_LIKED_PHOTOS_PAGE_SIZE

    def get_queryset(self):
        return get_user_liked_photos(
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        photos = []

        for photo in context["liked_photos"]:
            target = photo.album.user

            access = get_gallery_access_context(
                viewer=self.request.user,
                target=target,
            )

            if not access["can_view_profile"]:
                continue

            if not access["can_view_gallery"]:
                continue

            accessible_photo = get_photo_for_view(
                target=target,
                photo_id=photo.pk,
                access=access,
            )

            if accessible_photo is None:
                continue

            photos.append(accessible_photo)

        context["photos"] = photos
        context["pagination_url"] = reverse(
            "users:account_center_liked_photos",
        )
        context["pagination_target"] = "#liked-photos"

        return context


class AccountCenterFavoriteProfilesView(LoginRequiredMixin, ListView):
    """Display paginated favorite profiles."""

    template_name = "users/partials/account_center/favorite_profiles_list.html"
    context_object_name = "favorite_relations"

    def get_paginate_by(self, queryset):
        return getattr(
            settings,
            "ACCOUNT_CENTER_FAVORITE_PROFILES_PAGE_SIZE",
            10,
        )

    def get_queryset(self):
        return get_favorite_profiles(
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        relations = list(
            context["favorite_relations"],
        )

        user_ids = [relation.object_id for relation in relations]

        users_by_id = (
            User.objects.filter(pk__in=user_ids)
            .select_related(
                "profile",
                "profile__avatar_photo",
            )
            .in_bulk()
        )

        context["favorite_profiles"] = [
            users_by_id[relation.object_id] for relation in relations if relation.object_id in users_by_id
        ]

        context["pagination_url"] = reverse(
            "users:account_center_favorite_profiles",
        )
        context["pagination_target"] = "#fav-profiles"

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
            "favorites_count": get_favorites_count(user),
            "profile_favorites_count": get_profile_favorites_count(user),
            "gifts_received": 0,
            "blockers_count": get_blockers_count(user),
        }

        return context
