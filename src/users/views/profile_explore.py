from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from users.models import Profile

User = get_user_model()


class ProfileExploreView(TemplateView):
    template_name = "users/profile_explore.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile = get_object_or_404(Profile, user_id=self.kwargs["pk"])

        context["profile"] = profile
        context["profile_user"] = profile.user

        return context


class ProfileExplorePhotosView(View): ...


class ProfileExploreAlbumsView(View): ...


class ProfileExploreFriendsView(View): ...


class ProfileExploreMutualFriendsView(View): ...


class ProfileExplorePostsView(View): ...


class ProfileExploreVideosView(View): ...
