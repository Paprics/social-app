# src/users/views/avatar.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views import View
from django.views.generic import ListView

from gallery.selectors.photos import get_avatar_candidate_photos
from users.services.avatar import AvatarService
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse


class AvatarModalView(LoginRequiredMixin, View):
    """Render the profile avatar selection modal."""

    template_name = "users/partials/avatar_modal.html"

    def get(self, request):
        photos = get_avatar_candidate_photos(
            user=request.user,
        )

        return render(
            request,
            self.template_name,
            {
                "photos": photos,
                "current_avatar": request.user.profile.avatar_photo,
            },
        )


class AvatarSetView(LoginRequiredMixin, View):
    """Set an existing user photo as the profile avatar."""

    def post(self, request):
        photo_id = request.POST.get("photo_id")

        if not photo_id:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Photo ID is required.",
                },
                status=400,
            )

        try:
            photo_id = int(photo_id)
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Invalid photo ID.",
                },
                status=400,
            )

        try:
            photo = AvatarService.set_existing(
                user=request.user,
                photo_id=photo_id,
            )
        except PermissionDenied:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Photo does not exist or does not belong to this user.",
                },
                status=403,
            )

        return JsonResponse(
            {
                "ok": True,
                "photo_id": photo.pk,
                "avatar_url": photo.image.url,
            }
        )


class AvatarUploadView(LoginRequiredMixin, View):
    """Upload a new photo and set it as the profile avatar."""

    def post(self, request):
        file = request.FILES.get("photo")

        if not file:
            return HttpResponseBadRequest()

        AvatarService.upload_and_set(
            user=request.user,
            file=file,
        )

        return HttpResponse(status=204)


class AvatarRemoveView(LoginRequiredMixin, View):
    """Remove the current avatar without deleting its photo."""

    def post(self, request):
        AvatarService.remove(
            user=request.user,
        )

        return HttpResponse(status=204)


class AvatarModalView(LoginRequiredMixin, ListView):
    """Render the profile avatar selection modal."""

    template_name = "users/partials/avatar_modal.html"
    context_object_name = "photos"
    paginate_by = 5

    def get_queryset(self):
        return get_avatar_candidate_photos(
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["current_avatar"] = self.request.user.profile.avatar_photo

        return context


class AvatarPhotosView(LoginRequiredMixin, ListView):
    """Render one page of photos available for avatar selection."""

    template_name = "users/partials/avatar_photo_page.html"
    context_object_name = "photos"
    paginate_by = 5

    def get_queryset(self):
        return get_avatar_candidate_photos(
            user=self.request.user,
        )
