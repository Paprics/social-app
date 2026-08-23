# src/gallery/views/albums.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from gallery.forms import AlbumCreateForm
from gallery.selectors.albums import get_album_for_view
from gallery.selectors.photos import get_album_photos
from gallery.services.albums import (
    AlbumService,
    AlbumTypeUnavailableError,
    DuplicateAlbumTitleError,
    InvalidAlbumTitleError,
    InvalidAlbumTypeError,
    InvalidAlbumVisibilityError,
)
from gallery.services.photo_service import (
    InvalidPhotoTitleError,
    PhotoService,
)
from gallery.views.gallery import get_gallery_state


class AlbumDetailView(View):
    """
    Display one accessible gallery album.
    """

    template_name = "gallery/album_detail.html"

    def get(self, request, pk, album_pk):
        target, access, gallery_stats = get_gallery_state(
            request,
            pk,
        )

        album = get_album_for_view(
            target=target,
            album_id=album_pk,
            access=access,
        )

        if album is None:
            raise Http404

        album_photos = get_album_photos(
            album=album,
            access=access,
        )

        album_photos_count = album_photos.count()

        context = {
            "profile": target.profile,
            "profile_user": target,
            "is_owner": access["is_owner"],
            "gallery_stats": gallery_stats,
            "album": album,
            "album_photos": album_photos,
            "album_photos_count": album_photos_count,
        }

        return render(
            request,
            self.template_name,
            context,
        )


class AlbumSettingsView(LoginRequiredMixin, View):
    """
    Manage one album owned by the authenticated user.
    """

    template_name = "gallery/album_settings.html"

    def _get_album(self, request, pk, album_pk):
        if request.user.pk != pk:
            raise Http404

        target, access, gallery_stats = get_gallery_state(
            request,
            pk,
        )

        album = get_album_for_view(
            target=target,
            album_id=album_pk,
            access=access,
        )

        if album is None:
            raise Http404

        return target, access, gallery_stats, album

    def get(self, request, pk, album_pk):
        target, access, gallery_stats, album = self._get_album(
            request,
            pk,
            album_pk,
        )

        album_photos = get_album_photos(
            album=album,
            access=access,
        )

        return render(
            request,
            self.template_name,
            {
                "profile": target.profile,
                "profile_user": target,
                "is_owner": True,
                "gallery_stats": gallery_stats,
                "album": album,
                "album_photos": album_photos,
                # Temporary template compatibility.
                "photos": album_photos,
            },
        )

    def post(self, request, pk, album_pk):
        _, _, _, album = self._get_album(
            request,
            pk,
            album_pk,
        )

        action = request.POST.get(
            "action",
        )

        if action == "album":
            return self._update_album(
                request,
                pk,
                album,
            )

        if action == "photos":
            return self._update_photos(
                request,
                pk,
                album,
            )

        raise Http404

    def _update_album(
        self,
        request,
        pk,
        album,
    ):
        try:
            updated_album = AlbumService.update(
                user=request.user,
                album_id=album.pk,
                title=request.POST.get(
                    "title",
                    "",
                ),
                description=request.POST.get(
                    "description",
                    "",
                ),
                visibility=request.POST.get(
                    "visibility",
                    "",
                ),
                is_visible=bool(
                    request.POST.get(
                        "is_visible",
                    )
                ),
            )

        except (
            InvalidAlbumTitleError,
            InvalidAlbumVisibilityError,
            DuplicateAlbumTitleError,
        ) as error:
            return HttpResponse(
                str(error),
                status=422,
            )

        if updated_album is None:
            raise Http404

        return redirect(
            "gallery:album_detail",
            pk=pk,
            album_pk=album.pk,
        )

    def _update_photos(
        self,
        request,
        pk,
        album,
    ):
        updates = {}

        prefix = "photo_description_"

        for key, description in request.POST.items():
            if not key.startswith(prefix):
                continue

            photo_id = key.removeprefix(prefix)

            if not photo_id.isdigit():
                continue

            photo_id = int(photo_id)

            updates[photo_id] = {
                "description": description.strip()[:150],
                "is_visible": bool(request.POST.get(f"photo_visible_{photo_id}")),
            }

        updated = PhotoService.update_album_photos(
            user=request.user,
            album_id=album.pk,
            updates=updates,
        )

        if not updated:
            raise Http404

        return redirect(
            "gallery:album_detail",
            pk=pk,
            album_pk=album.pk,
        )


class AlbumCreateView(LoginRequiredMixin, View):
    """
    Validate request data and delegate album creation to AlbumService.
    """

    def post(self, request, album_type):
        form = AlbumCreateForm(
            request.POST,
        )

        if not form.is_valid():
            return self._form_error_response(
                form,
            )

        try:
            album = AlbumService.create(
                user=request.user,
                title=form.cleaned_data["title"],
                visibility=form.cleaned_data["visibility"],
                album_type=album_type,
            )

        except DuplicateAlbumTitleError as error:
            form.add_error(
                "title",
                error,
            )

            return self._form_error_response(
                form,
            )

        except InvalidAlbumVisibilityError as error:
            form.add_error(
                "visibility",
                error,
            )

            return self._form_error_response(
                form,
            )

        except (
            InvalidAlbumTypeError,
            AlbumTypeUnavailableError,
        ) as error:
            form.add_error(
                None,
                error,
            )

            return self._form_error_response(
                form,
            )

        return JsonResponse(
            {
                "success": True,
                "redirect_url": reverse(
                    "gallery:album_detail",
                    kwargs={
                        "pk": request.user.pk,
                        "album_pk": album.pk,
                    },
                ),
            },
        )

    @staticmethod
    def _form_error_response(form):
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors.get_json_data(),
            },
            status=422,
        )


class AlbumDeleteView(LoginRequiredMixin, View):
    """
    Delete an album owned by the authenticated user.
    """

    def post(self, request, pk, album_pk):
        if request.user.pk != pk:
            raise Http404

        deleted = AlbumService.delete(
            user=request.user,
            album_id=album_pk,
        )

        if not deleted:
            raise Http404

        return redirect(
            "gallery:gallery",
            pk=request.user.pk,
        )
