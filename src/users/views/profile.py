# src/users/views/profile.py
"""HTTP view for user profile pages."""

from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

from users.selectors.user_block import get_block_state
from users.services.profile_context import ProfileContextBuilder

User = get_user_model()


class ProfileView(View):
    """Render a user profile page."""

    template_name = "users/profile.html"
    blocked_template_name = "users/profile_blocked.html"

    def get(self, request, pk):
        try:
            context = ProfileContextBuilder.build_profile(
                request,
                pk,
            )
        except Http404:
            blocked_response = self._render_blocked_profile(
                request=request,
                pk=pk,
            )

            if blocked_response is not None:
                return blocked_response

            raise

        return render(
            request,
            self.template_name,
            context,
        )

    def _render_blocked_profile(self, *, request, pk):
        """Render a blocked-profile notice only when target blocked viewer."""

        if not request.user.is_authenticated:
            return None

        target_user = get_object_or_404(
            User.objects.only(
                "pk",
                "username",
            ),
            pk=pk,
        )

        block_state = get_block_state(
            request.user,
            target_user,
        )

        if not block_state["target_has_blocked"]:
            return None

        return render(
            request,
            self.blocked_template_name,
            {
                "target_user": target_user,
                "is_blocked": True,
                "viewer_has_blocked": False,
                "target_has_blocked": True,
            },
            status=200,
        )
