# src/users/views/block.py
"""HTTP actions for blocking and unblocking users."""

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from users.selectors.user_block import get_user_block_counts
from users.services.user_block import UserBlockService

User = get_user_model()


def _is_account_center_request(request) -> bool:
    """Return whether the action originated from Account Center."""

    return request.GET.get("context") == "account_center"


def _render_block_button(request, *, target_user, viewer_has_blocked):
    """Render the block/unblock control for the target user."""

    response = render(
        request,
        "users/partials/block_button.html",
        {
            "target_user": target_user,
            "viewer_has_blocked": viewer_has_blocked,
        },
    )

    response["HX-Trigger"] = "blockChanged"

    return response


def _render_account_center_success(request):
    """Render OOB block counters after an Account Center mutation."""

    response = render(
        request,
        "users/partials/account_center/_block_counts_oob.html",
        {
            "block_counts": get_user_block_counts(
                request.user,
            ),
        },
    )

    response["HX-Trigger"] = "blockChanged"

    return response


class UserBlockCreateView(LoginRequiredMixin, View):
    """Block another user."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        UserBlockService.block(
            request.user,
            target_user,
        )

        if _is_account_center_request(request):
            return _render_account_center_success(request)

        return _render_block_button(
            request,
            target_user=target_user,
            viewer_has_blocked=True,
        )


class UserBlockDeleteView(LoginRequiredMixin, View):
    """Remove a block created by the current user."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        UserBlockService.unblock(
            request.user,
            target_user,
        )

        if _is_account_center_request(request):
            return _render_account_center_success(request)

        return _render_block_button(
            request,
            target_user=target_user,
            viewer_has_blocked=False,
        )
