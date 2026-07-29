# src/users/views/profile.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views import View

from users.models.gallery import Photo
from users.models.profile import Profile
from users.services.gallery import get_or_create_default_album, get_remaining_slots
from users.services.PhotoService import process_image
from users.validators.image import validate_uploaded_image
from users.services.friendship_service import FriendshipService


class ProfileView(View):
    template_name = "users/profile.html"

    def get(self, request, pk):
        profile = get_object_or_404(Profile, user_id=pk)
        profile_user = profile.user
        albums = profile_user.galleries.filter(is_visible=True).prefetch_related("photos")

        context = {
            "profile": profile,
            "profile_user": profile_user,
            "is_owner": request.user == profile_user,
            "albums": albums[:3],
            "friendship": FriendshipService.get_relation(
                request.user,
                profile_user,
            ),
        }

        return render(request, self.template_name, context)


class AvatarModalView(LoginRequiredMixin, View):
    """GET — возвращает HTML модального окна выбора аватара."""

    template_name = "users/partials/avatar_modal.html"

    def get(self, request):
        photos = (
            Photo.objects.filter(
                album__user=request.user,
                is_visible=True,
            )
            .select_related("album")
            .order_by("-created_at")
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
    """POST — устанавливает существующее фото аватаром профиля."""

    def post(self, request):
        photo_id = request.POST.get("photo_id")
        if not photo_id:
            return HttpResponseBadRequest()

        photo = get_object_or_404(Photo, pk=photo_id, album__user=request.user)
        profile = request.user.profile
        profile.avatar_photo = photo
        profile.save(update_fields=["avatar_photo"])

        print(f"[profile] Аватар пользователя {request.user.pk} → Photo #{photo.pk}")

        # HTMX обновляет блок аватара без перезагрузки страницы
        return render(
            request,
            "users/partials/avatar_block.html",
            {
                "profile_user": request.user,
            },
        )


class AvatarUploadView(LoginRequiredMixin, View):
    """
    POST — загружает новое фото, кладёт в дефолтный альбом,
    ставит аватаром, возвращает обновлённый блок аватара.
    """

    def post(self, request):
        file = request.FILES.get("photo")
        if not file:
            return HttpResponseBadRequest()

        # Валидация
        try:
            validate_uploaded_image(file)
        except Exception as exc:
            return HttpResponse(str(exc), status=422)

        # Проверяем лимит
        if get_remaining_slots(request.user) <= 0:
            return HttpResponse("Photo limit reached.", status=422)

        # Обрабатываем и сохраняем
        processed = process_image(file)
        album = get_or_create_default_album(request.user)
        photo = Photo(album=album, image=processed, title=file.name)
        photo.save()

        # Ставим аватаром
        profile = request.user.profile
        profile.avatar_photo = photo
        profile.save(update_fields=["avatar_photo"])

        print(f"[profile] Загружен и установлен новый аватар для пользователя {request.user.pk}, Photo #{photo.pk}")

        return render(
            request,
            "users/partials/avatar_block.html",
            {
                "profile_user": request.user,
            },
        )
