# src/users/views/friendship.py
"""HTTP actions for friend requests and accepted friendships."""

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from users.selectors.friendship import get_friendship_counts
from users.services.friendship_errors import FriendshipError
from users.services.friendship_service import FriendshipService

User = get_user_model()

ACCOUNT_CENTER_CONTEXT = "account_center"


def _is_account_center_request(request):
    """Return whether the action originated from Account Center."""

    return request.GET.get("context") == ACCOUNT_CENTER_CONTEXT


def _render_friendship_actions(request, target_user):
    """Render friendship controls displayed on a user's profile."""

    friendship = FriendshipService.get_relation(
        request.user,
        target_user,
    )

    return render(
        request,
        "users/partials/friendship_actions.html",
        {
            "target_user": target_user,
            "friendship": friendship,
        },
    )


def _render_account_center_success(request):
    """Render OOB Account Center counters after a successful mutation."""

    return render(
        request,
        "users/partials/account_center/_friendship_counts_oob.html",
        {
            "friendship_counts": get_friendship_counts(
                request.user,
            ),
        },
    )


def _success_response(request, target_user):
    """
    Return the appropriate HTMX response after a successful mutation.

    Account Center removes the affected row, updates friendship counters,
    and refreshes the active friendship tab through an HTMX event.
    Profile pages redraw the friendship action controls.
    """

    if _is_account_center_request(request):
        response = _render_account_center_success(
            request,
        )
    else:
        response = _render_friendship_actions(
            request,
            target_user,
        )

    response["HX-Trigger"] = "friendshipChanged"

    return response


def _error_response(request, target_user):
    """
    Recover from stale or duplicate friendship actions.

    Account Center keeps the current row unchanged.
    Profile pages redraw the authoritative current state.
    """

    if _is_account_center_request(request):
        return HttpResponse(status=204)

    return _render_friendship_actions(
        request,
        target_user,
    )


def _execute_action(request, target_user, action):
    """Execute one friendship command and convert domain errors to safe UI responses."""

    try:
        action(
            request.user,
            target_user,
        )
    except FriendshipError:
        return _error_response(
            request,
            target_user,
        )

    return _success_response(
        request,
        target_user,
    )


class FriendRequestSendView(LoginRequiredMixin, View):
    """Send a friend request to another user."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        return _execute_action(
            request,
            target_user,
            FriendshipService.send_request,
        )


class FriendRequestCancelView(LoginRequiredMixin, View):
    """Cancel the current user's outgoing friend request."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        return _execute_action(
            request,
            target_user,
            FriendshipService.cancel_request,
        )


class FriendRequestDeclineView(LoginRequiredMixin, View):
    """Decline an incoming friend request."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        return _execute_action(
            request,
            target_user,
            FriendshipService.decline_request,
        )


class FriendRequestAcceptView(LoginRequiredMixin, View):
    """Accept an incoming friend request."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        return _execute_action(
            request,
            target_user,
            FriendshipService.accept_request,
        )


class FriendRemoveView(LoginRequiredMixin, View):
    """Remove an accepted friendship."""

    def post(self, request, pk):
        target_user = get_object_or_404(
            User,
            pk=pk,
        )

        return _execute_action(
            request,
            target_user,
            FriendshipService.remove_friend,
        )
