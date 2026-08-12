# src/gallery/views/photos.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse, JsonResponse
from django.views import View

from gallery.forms import PhotoUploadForm
from gallery.services.photo_service import PhotoService


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
