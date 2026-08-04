from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from users.services.user_block import UserBlockService

User = get_user_model()


class UserBlockCreateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        UserBlockService.block(
            request.user,
            target,
        )

        return render(
            request,
            "users/partials/block_button.html",
            {
                "profile": target.profile,
                "is_blocked": True,
            },
        )


class UserBlockDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        UserBlockService.unblock(
            request.user,
            target,
        )

        return render(
            request,
            "users/partials/block_button.html",
            {
                "profile": target.profile,
                "is_blocked": False,
            },
        )
