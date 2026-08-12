# src/search/views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import ListView

from search.forms import UserSearchForm
from search.selectors import get_users_for_search
from django.conf import settings
from geo.models import Country
from users.models import Profile


class UserSearchView(LoginRequiredMixin, ListView):
    template_name = "search/search.html"
    context_object_name = "profiles"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.headers.get("HX-Request") != "true":
            context["countries"] = Country.objects.filter(
                code2__in=settings.GEO_ALLOWED_COUNTRIES,
            )

        context["age_choices"] = range(18, 81)
        context["gender_choices"] = Profile.Gender.choices

        return context

    def get_queryset(self):
        form = UserSearchForm(self.request.GET)

        if not form.is_valid():
            raise Http404

        return get_users_for_search(
            request_user=self.request.user,
            filters=form.cleaned_data,
        )

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["search/partials/results.html"]

        return [self.template_name]
