from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

from gallery.selectors.gallery import get_gallery_access_context
from gallery.selectors.photos import (
    get_photo_for_view,
    get_photo_target_user,
)
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
        target = get_photo_target_user(
            photo_id=pk,
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
            photo_id=pk,
            access=access,
        )

        if photo is None:
            raise Http404

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
