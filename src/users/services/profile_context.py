# src/users/services/profile_context.py

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.urls import reverse

from gallery.selectors.albums import get_profile_albums
from messenger.services.access import MessengerAccessService
from posts.services.access import PostAccessService
from users.services.access import ProfileAccessService
from users.services.favorite_service import FavoriteService
from users.services.friendship_service import FriendshipService
from users.services.profile_visits import ProfileVisitService
from users.services.user_block import UserBlockService

User = get_user_model()


class ProfileContextBuilder:
    """Build context for user profile pages."""

    # =========================================================================
    # Public API
    # =========================================================================

    @classmethod
    def build_profile(cls, request, pk):
        """Build context for the main profile page."""

        target_user = cls._get_target_user(pk)

        cls._record_visit(
            viewer=request.user,
            target=target_user,
        )

        return cls._build_common_context(
            request=request,
            target_user=target_user,
        )

    @classmethod
    def build_explore(cls, request, pk):
        """Build context for the extended profile page."""

        target_user = cls._get_target_user(pk)

        cls._record_visit(
            viewer=request.user,
            target=target_user,
        )

        context = cls._build_common_context(
            request=request,
            target_user=target_user,
        )

        # ---------------------------------------------------------------------
        # Explore-specific context
        # ---------------------------------------------------------------------

        # Additional explore-specific data will be added here later.

        return context

    # =========================================================================
    # Target user
    # =========================================================================

    @staticmethod
    def _get_target_user(pk):
        """Return the profile owner with required related data."""

        return get_object_or_404(
            User.objects.select_related(
                "profile",
                "settings",
                "premium_features",
            ),
            pk=pk,
        )

    # =========================================================================
    # Profile visits
    # =========================================================================

    @staticmethod
    def _record_visit(*, viewer, target):
        """Record an authenticated user's profile visit."""

        if not viewer.is_authenticated:
            return

        if viewer == target:
            return

        ProfileVisitService.record(
            viewer.id,
            target.id,
        )

    # =========================================================================
    # Main context builder
    # =========================================================================

    @classmethod
    def _build_common_context(cls, *, request, target_user):
        """Build context shared by profile and explore pages."""

        viewer = request.user

        # =====================================================================
        # Relationship state
        # =====================================================================

        friendship = cls._get_friendship(
            viewer=viewer,
            target=target_user,
        )

        is_friend = friendship["is_friend"] if friendship else False

        is_blocked = cls._get_is_blocked(
            viewer=viewer,
            target=target_user,
        )

        # =====================================================================
        # Access services
        # =====================================================================

        profile_access = ProfileAccessService(
            viewer=viewer,
            target=target_user,
            is_friend=is_friend,
        )

        messenger_access = MessengerAccessService(
            viewer=viewer,
            target=target_user,
            is_friend=is_friend,
            is_blocked=is_blocked,
        )

        post_access = PostAccessService(
            viewer=viewer,
            target=target_user,
            is_friend=is_friend,
        )

        # =====================================================================
        # Access context
        # =====================================================================

        access = {
            # Profile
            "can_view_profile": profile_access.can_view_profile(),
            "can_view_friends": profile_access.can_view_friends(),
            # Messenger
            "can_send_message": messenger_access.can_send_message(),
            # Wall
            "can_view_wall": post_access.can_view_wall(),
            "can_post_on_wall": post_access.can_post_on_wall(),
        }

        # =====================================================================
        # Gallery
        # =====================================================================

        albums = []
        albums_count = 0

        if access["can_view_profile"]:
            albums, albums_count = get_profile_albums(
                viewer=viewer,
                target=target_user,
                is_friend=is_friend,
                limit=3,
                preview_limit=4,
            )

        # =====================================================================
        # Friends
        # =====================================================================

        friends = []
        friends_count = 0

        if access["can_view_friends"]:
            friends = FriendshipService.get_friends_preview(
                target_user,
                limit=6,
            )

            friends_count = FriendshipService.get_friends_count(
                target_user,
            )

        # =====================================================================
        # Mutual friends
        # =====================================================================

        mutual_friends = []
        mutual_friends_count = 0

        if viewer.is_authenticated and viewer != target_user and access["can_view_friends"]:
            mutual_friends_queryset = FriendshipService.get_mutual_friends(
                viewer,
                target_user,
            )

            mutual_friends_count = mutual_friends_queryset.count()

            if mutual_friends_count:
                mutual_friends = list(mutual_friends_queryset[:6])

        # =====================================================================
        # Favorites
        # =====================================================================

        favorite_url = reverse(
            "users:user_favorite_toggle",
            kwargs={"pk": target_user.pk},
        )

        is_favorite = cls._get_is_favorite(
            viewer=viewer,
            target=target_user,
        )

        # =====================================================================
        # Final context
        # =====================================================================

        return {
            # -----------------------------------------------------------------
            # Profile
            # -----------------------------------------------------------------
            "target_user": target_user,
            "is_owner": viewer == target_user,
            # -----------------------------------------------------------------
            # Access
            # -----------------------------------------------------------------
            "access": access,
            # -----------------------------------------------------------------
            # Gallery
            # -----------------------------------------------------------------
            "albums": albums,
            "albums_count": albums_count,
            # -----------------------------------------------------------------
            # Friendship
            # -----------------------------------------------------------------
            "friendship": friendship,
            "friends": friends,
            "friends_count": friends_count,
            "mutual_friends": mutual_friends,
            "mutual_friends_count": mutual_friends_count,
            # -----------------------------------------------------------------
            # Favorites
            # -----------------------------------------------------------------
            "favorite_url": favorite_url,
            "is_favorite": is_favorite,
            # -----------------------------------------------------------------
            # Blocking
            # -----------------------------------------------------------------
            "is_blocked": is_blocked,
        }

    # =========================================================================
    # Friendship helpers
    # =========================================================================

    @staticmethod
    def _get_friendship(*, viewer, target):
        """Return friendship state for authenticated viewers."""

        if not viewer.is_authenticated:
            return None

        return FriendshipService.get_relation(
            viewer,
            target,
        )

    # =========================================================================
    # Favorite helpers
    # =========================================================================

    @staticmethod
    def _get_is_favorite(*, viewer, target):
        """Return whether target user is in viewer's favorites."""

        if not viewer.is_authenticated:
            return False

        return FavoriteService.is_favorite(
            viewer,
            target,
        )

    # =========================================================================
    # Block helpers
    # =========================================================================

    @staticmethod
    def _get_is_blocked(*, viewer, target):
        """Return whether either user has blocked the other."""

        if not viewer.is_authenticated:
            return False

        return UserBlockService.is_blocked(
            viewer,
            target,
        )
