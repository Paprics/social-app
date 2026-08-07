# src/users/services/profile_page.py
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.urls import reverse

from users.services.favorite_service import FavoriteService
from users.services.friendship_service import FriendshipService
from users.services.profile_access import ProfileAccessService
from users.services.profile_visits import ProfileVisitService
from users.services.user_block import UserBlockService

User = get_user_model()


class ProfilePageService:

    @classmethod
    def profile(cls, request, pk):
        target_user = cls._get_target_user(pk)

        if request.user.is_authenticated:
            ProfileVisitService.record(
                request.user.id,
                target_user.id,
            )

        return cls._build_context(request, target_user)

    @classmethod
    def explore(cls, request, pk):
        target_user = cls._get_target_user(pk)
        return cls._build_context(request, target_user)

    @staticmethod
    def _get_target_user(pk):
        return get_object_or_404(
            User.objects.select_related(
                "profile",
                "settings",
                "premium_features",
            ),
            pk=pk,
        )

    @staticmethod
    def _build_context(request, target_user):

        if request.user.is_authenticated:
            friendship = FriendshipService.get_relation(
                request.user,
                target_user,
            )

            is_favorite = FavoriteService.is_favorite(
                request.user,
                target_user,
            )

            is_blocked = UserBlockService.is_blocked(
                request.user,
                target_user,
            )
        else:
            friendship = None
            is_favorite = False
            is_blocked = False

        permissions = ProfileAccessService(
            viewer=request.user,
            target=target_user,
            friendship=friendship,
        )

        albums = target_user.galleries.filter(is_visible=True).prefetch_related("photos")

        return {
            "target_user": target_user,
            "is_owner": request.user == target_user,
            "albums": albums[:3],
            "friendship": friendship,
            "permissions": permissions,
            "favorite_url": reverse(
                "users:user_favorite_toggle",
                kwargs={"pk": target_user.pk},
            ),
            "is_favorite": is_favorite,
            "is_blocked": is_blocked,
            "friends": FriendshipService.get_friends_preview(
                target_user,
                limit=6,
            ),
            "friends_count": FriendshipService.get_friends_count(
                target_user,
            ),
        }
