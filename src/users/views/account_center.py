from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AccountCenterView(LoginRequiredMixin, TemplateView):
    template_name = "users/account_center.html"
