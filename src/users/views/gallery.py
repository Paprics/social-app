# src/users/views/gallery.py
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from users.forms.gallery import PhotoUploadForm
from users.models.gallery import Photo, UserAlbum
from users.models.profile import Profile
from users.services.gallery import get_remaining_slots, upload_photos


class GalleryView(LoginRequiredMixin, View):
    template_name = "users/gallery.html"

    def get(self, request, pk):
        profile = get_object_or_404(Profile, user_id=pk)
        photos = Photo.objects.filter(
            album__user=profile.user,
            is_visible=True,
        ).select_related("album")
        albums = profile.user.galleries.filter(is_visible=True)
        context = {
            "profile": profile,
            "profile_user": profile.user,
            "is_owner": request.user == profile.user,
            "albums": albums,
            "albums_count": albums.count(),
            "photos": photos,
            "photos_count": photos.count(),
            "max_photos": settings.GALLERY_MAX_PHOTOS,
            "remaining_slots": get_remaining_slots(profile.user),
        }
        return render(request, self.template_name, context)


class PhotoUploadView(LoginRequiredMixin, View):
    """HTMX endpoint для пакетной загрузки фотографий."""

    def post(self, request):
        form = PhotoUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return HttpResponse(status=422)

        files = form.cleaned_data["photos"]
        upload_photos(request.user, files)
        return HttpResponse(status=200)


class AlbumDetailView(LoginRequiredMixin, View):
    template_name = "users/album_detail.html"

    def get(self, request, pk, album_pk):
        profile = get_object_or_404(Profile, user_id=pk)
        album = get_object_or_404(UserAlbum, pk=album_pk, user=profile.user)
        is_owner = request.user == profile.user

        # Чужой закрытый альбом — 403
        if not is_owner and not album.is_visible:
            return HttpResponseForbidden()

        photos = album.photos.filter(is_visible=True)
        if is_owner:
            photos = album.photos.all()

        context = {
            "profile": profile,
            "profile_user": profile.user,
            "album": album,
            "photos": photos,
            "photos_count": photos.count(),
            "is_owner": is_owner,
            "remaining_slots": get_remaining_slots(profile.user) if is_owner else 0,
            "max_photos": settings.GALLERY_MAX_PHOTOS,
        }
        return render(request, self.template_name, context)


class AlbumSettingsView(LoginRequiredMixin, View):
    template_name = "users/album_settings.html"

    def _get_album(self, request, pk, album_pk):
        profile = get_object_or_404(Profile, user_id=pk)
        if request.user != profile.user:
            return None, None, HttpResponseForbidden()
        album = get_object_or_404(UserAlbum, pk=album_pk, user=profile.user)
        return profile, album, None

    def get(self, request, pk, album_pk):
        profile, album, forbidden = self._get_album(request, pk, album_pk)
        if forbidden:
            return forbidden
        photos = album.photos.all()
        return render(
            request,
            self.template_name,
            {
                "profile": profile,
                "profile_user": profile.user,
                "album": album,
                "photos": photos,
            },
        )

    def post(self, request, pk, album_pk):
        profile, album, forbidden = self._get_album(request, pk, album_pk)
        if forbidden:
            return forbidden

        action = request.POST.get("action")

        if action == "album":
            album.title = request.POST.get("title", album.title).strip()
            album.description = request.POST.get("description", "").strip()
            album.visibility = request.POST.get("visibility", album.visibility)
            album.is_visible = bool(request.POST.get("is_visible"))
            album.save()
            print(f"[gallery] Альбом #{album.pk} обновлён пользователем {request.user.pk}")

        elif action == "photos":
            for photo in album.photos.all():
                title = request.POST.get(f"photo_title_{photo.pk}", "").strip()
                visible = bool(request.POST.get(f"photo_visible_{photo.pk}"))
                photo.title = title
                photo.is_visible = visible
                photo.save()
            print(f"[gallery] Фотографии альбома #{album.pk} обновлены")

        return redirect("users:album_detail", pk=pk, album_pk=album_pk)


class PhotoDeleteView(LoginRequiredMixin, View):
    """Удаление одного фото. Только владелец."""

    def post(self, request, photo_pk):
        photo = get_object_or_404(Photo, pk=photo_pk)
        if photo.album.user != request.user:
            return HttpResponseForbidden()

        album_pk = photo.album_id
        user_pk = request.user.pk

        # Удаляем файл с диска
        try:
            photo.image.delete(save=False)
        except Exception as exc:
            print(f"[gallery] Не удалось удалить файл: {exc}")

        photo.delete()
        print(f"[gallery] Фото #{photo_pk} удалено пользователем {request.user.pk}")

        return HttpResponse(status=200)
