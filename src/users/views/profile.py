# users/view/profile.py
import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)
User = get_user_model()


class ProfileView(TemplateView):
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(User, pk=self.kwargs["pk"])
        context["profile_user"] = profile_user
        context["is_owner"] = profile_user == self.request.user
        logger.debug(
            "ProfileView: user_id=%s viewed by user_id=%s",
            profile_user.pk,
            self.request.user.pk,
        )
        return context
