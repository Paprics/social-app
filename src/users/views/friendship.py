from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from users.services.friendship_service import FriendshipService

User = get_user_model()


def _render_friendship_actions(request, profile_user):
    friendship = FriendshipService.get_relation(
        request.user,
        profile_user,
    )

    return render(
        request,
        "users/partials/friendship_actions.html",
        {
            "profile_user": profile_user,
            "friendship": friendship,
        },
    )


class FriendRequestSendView(LoginRequiredMixin, View):

    def post(self, request, pk):

        print(f"=================================================================\nCALL FriendRequestSendView")

        profile_user = get_object_or_404(User, pk=pk)

        FriendshipService.send_request(
            request.user,
            profile_user,
        )

        friendship = FriendshipService.get_relation(
            request.user,
            profile_user,
        )

        return _render_friendship_actions(
            request,
            profile_user,
        )


class FriendRequestCancelView(LoginRequiredMixin, View):

    def post(self, request, pk):

        profile_user = get_object_or_404(User, pk=pk)

        FriendshipService.cancel_request(
            request.user,
            profile_user,
        )

        return _render_friendship_actions(
            request,
            profile_user,
        )


class FriendRequestDeclineView(LoginRequiredMixin, View):

    def post(self, request, pk):

        profile_user = get_object_or_404(User, pk=pk)

        FriendshipService.decline_request(
            request.user,
            profile_user,
        )

        return _render_friendship_actions(
            request,
            profile_user,
        )


class FriendRequestAcceptView(LoginRequiredMixin, View):

    def post(self, request, pk):

        profile_user = get_object_or_404(User, pk=pk)

        FriendshipService.accept_request(
            request.user,
            profile_user,
        )

        return _render_friendship_actions(
            request,
            profile_user,
        )


class FriendRemoveView(LoginRequiredMixin, View):

    def post(self, request, pk):
        profile_user = get_object_or_404(User, pk=pk)

        FriendshipService.remove_friend(
            request.user,
            profile_user,
        )

        return _render_friendship_actions(
            request,
            profile_user,
        )
