# src/users/views/profile.py

from django.shortcuts import render
from django.views import View

from users.services.profile_context import ProfileContextBuilder


class ProfileView(View):
    """Render a user profile page."""

    template_name = "users/profile.html"

    def get(self, request, pk):
        context = ProfileContextBuilder.build_profile(
            request,
            pk,
        )

        return render(
            request,
            self.template_name,
            context,
        )
