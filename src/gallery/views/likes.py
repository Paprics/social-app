# src/gallery/views/likes.py

"""Views for gallery photo likes."""

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views import View

from gallery.selectors.gallery import get_gallery_access_context
from gallery.selectors.likes import (
    get_photo_likers,
    get_photo_likes_count,
)
from gallery.selectors.photos import (
    get_photo_for_view,
    get_photo_target_user,
)
from gallery.services.likes import LikeService


def _get_accessible_photo(*, request, photo_pk):
    """Return a photo accessible to the current viewer."""

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

    return photo


class PhotoLikeToggleView(LoginRequiredMixin, View):
    """Toggle the authenticated user's like on a photo."""

    template_name = "gallery/partials/likes/_button.html"

    def post(self, request, photo_pk):
        photo = _get_accessible_photo(
            request=request,
            photo_pk=photo_pk,
        )

        is_liked = LikeService.toggle(
            user=request.user,
            photo=photo,
        )

        return render(
            request,
            self.template_name,
            {
                "photo": photo,
                "is_liked": is_liked,
                "likes_count": get_photo_likes_count(
                    photo=photo,
                ),
            },
        )


class PhotoLikesListView(LoginRequiredMixin, View):
    """Return users who liked a photo."""

    template_name = "gallery/partials/likes/_users_page.html"
    paginate_by = settings.NOTIFICATIONS_PAGE_SIZE

    def get(self, request, photo_pk):
        photo = _get_accessible_photo(
            request=request,
            photo_pk=photo_pk,
        )

        paginator = Paginator(
            get_photo_likers(
                photo=photo,
            ),
            self.paginate_by,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "photo": photo,
                "page_obj": page_obj,
                "likers": page_obj.object_list,
            },
        )
