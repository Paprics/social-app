from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from gallery.models import Photo
from users.services.favorite_service import FavoriteService

User = get_user_model()


class UserFavoriteToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(
            User,
            pk=pk,
        )

        is_favorite = FavoriteService.toggle(
            request.user,
            user,
        )

        return render(
            request,
            "users/partials/favorite_button.html",
            {
                "favorite_url": request.path,
                "is_favorite": is_favorite,
            },
        )


class PhotoFavoriteToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        photo = get_object_or_404(
            Photo,
            pk=pk,
        )

        is_favorite = FavoriteService.toggle(
            request.user,
            photo,
        )

        return render(
            request,
            "users/partials/photo_favorite_button.html",
            {
                "photo": photo,
                "is_favorite": is_favorite,
            },
        )
