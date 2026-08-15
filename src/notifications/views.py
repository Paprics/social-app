# src/notifications/views.py

"""Notification HTTP views."""

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView

from notifications.models import Notification
from notifications.selectors import get_user_notifications
from notifications.services import NotificationService


def _refresh_response():
    """Return an HTMX response that refreshes the current page."""

    response = HttpResponse()
    response["HX-Refresh"] = "true"

    return response


class NotificationListView(LoginRequiredMixin, ListView):
    """Return one paginated page of the user's notifications."""

    template_name = "notifications/partials/_notification_page.html"
    context_object_name = "notification_items"
    paginate_by = settings.NOTIFICATIONS_PAGE_SIZE

    def get_queryset(self):
        kind = self.request.GET.get("kind")

        if kind not in Notification.Kind.values:
            kind = None

        self.current_kind = kind

        return get_user_notifications(
            user=self.request.user,
            kind=kind,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["current_kind"] = self.current_kind

        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    """Mark one notification as read."""

    def post(self, request, notification_id):
        NotificationService.mark_read(
            recipient=request.user,
            notification_id=notification_id,
        )

        return _refresh_response()


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """Mark all current user's notifications as read."""

    def post(self, request):
        NotificationService.mark_all_read(
            recipient=request.user,
        )

        return _refresh_response()
