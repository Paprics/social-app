# src/users/services/profile_context/builder.py
"""Build context for profile and Profile Explore pages."""

from django.http import Http404

from users.selectors.friendship import get_mutual_friends_count
from users.services.profile_visits import ProfileVisitService

from .access_context import build_access_context
from .content import build_profile_content
from .relationships import build_relationship_context
from .target import get_profile_target


class ProfileContextBuilder:
    """Build context for profile-related pages."""

    @classmethod
    def build_profile(cls, request, pk):
        """Build full context for the main profile page."""

        target = get_profile_target(pk)

        context, is_friend = cls._build_base_context(
            request=request,
            target=target,
        )

        cls._record_visit(
            viewer=request.user,
            target=target,
            is_blocked=context["is_blocked"],
        )

        content = build_profile_content(
            viewer=request.user,
            target=target,
            is_friend=is_friend,
            access=context["access"],
        )

        return {
            **context,
            **content,
        }

    @classmethod
    def build_explore(cls, request, pk):
        """Build lightweight shared context for the Explore page."""

        target = get_profile_target(pk)
        viewer = request.user

        context, _ = cls._build_base_context(
            request=request,
            target=target,
        )

        cls._record_visit(
            viewer=viewer,
            target=target,
            is_blocked=context["is_blocked"],
        )

        mutual_friends_count = 0

        if viewer.is_authenticated and viewer != target and context["access"]["can_view_friends"]:
            mutual_friends_count = get_mutual_friends_count(
                viewer,
                target,
            )

        context["mutual_friends_count"] = mutual_friends_count

        return context

    @staticmethod
    def _record_visit(*, viewer, target, is_blocked=False):
        """Record an authenticated, non-blocked visit to another profile."""

        if not viewer.is_authenticated:
            return

        if viewer == target:
            return

        if is_blocked:
            return

        ProfileVisitService.record(
            viewer.pk,
            target.pk,
        )

    @staticmethod
    def _build_base_context(*, request, target):
        """Build shared public context and relationship state."""

        viewer = request.user

        relationship = build_relationship_context(
            viewer=viewer,
            target=target,
        )

        if relationship["target_has_blocked"]:
            raise Http404

        is_friend = relationship["is_friend"]

        access = build_access_context(
            viewer=viewer,
            target=target,
            is_friend=is_friend,
            is_blocked=relationship["is_blocked"],
            target_has_blocked=relationship["target_has_blocked"],
        )

        context = {
            "target_user": target,
            "is_owner": viewer == target,
            "access": access,
            "friendship": relationship["friendship"],
            "favorite_url": relationship["favorite_url"],
            "is_favorite": relationship["is_favorite"],
            "is_blocked": relationship["is_blocked"],
            "viewer_has_blocked": relationship["viewer_has_blocked"],
            "target_has_blocked": relationship["target_has_blocked"],
        }

        return context, is_friend
