# src/gallery/views/photos.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from gallery.forms import PhotoUploadForm
from gallery.selectors.gallery import get_gallery_access_context
from gallery.selectors.photos import (
    get_photo_for_view,
    get_photo_target_user,
)
from gallery.services.photo_service import PhotoService
from users.services.favorite_service import FavoriteService


class PhotoLightboxDetailView(View):
    """Render the detail block displayed below a photo in the lightbox."""

    template_name = "gallery/partials/_lightbox_photo_detail.html"

    def get(self, request, photo_pk):
        target = get_photo_target_user(
            photo_id=photo_pk,
        )

        if target is None:
            raise Http404

        access = get_gallery_access_context(
            viewer=request.user,
            target=target,
        )

        if not access["can_view_profile"]:
            raise Http404

        if not access["can_view_gallery"]:
            raise PermissionDenied

        photo = get_photo_for_view(
            target=target,
            photo_id=photo_pk,
            access=access,
        )

        if photo is None:
            raise Http404

        is_favorite = False

        if request.user.is_authenticated:
            is_favorite = FavoriteService.is_favorite(
                request.user,
                photo,
            )

        return render(
            request,
            self.template_name,
            {
                "photo": photo,
                "photo_owner": target,
                "is_favorite": is_favorite,
            },
        )


class PhotoUploadView(LoginRequiredMixin, View):
    """
    Upload photos into a concrete user-created album.
    """

    def post(self, request, pk, album_pk):
        if request.user.pk != pk:
            raise Http404

        form = PhotoUploadForm(
            request.POST,
            request.FILES,
        )

        if not form.is_valid():
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors.get_json_data(),
                },
                status=422,
            )

        result = PhotoService.upload_to_album(
            user=request.user,
            album_id=album_pk,
            files=form.cleaned_data["photos"],
        )

        if result is None:
            raise Http404

        return JsonResponse(
            {
                "success": True,
                "saved": len(result["saved"]),
                "skipped": result["skipped"],
            },
        )


class PhotoDeleteView(LoginRequiredMixin, View):
    """
    Delete one photo owned by the authenticated user.
    """

    def post(self, request, photo_pk):
        deleted = PhotoService.delete(
            user=request.user,
            photo_id=photo_pk,
        )

        if not deleted:
            raise Http404

        return HttpResponse(
            status=200,
        )
