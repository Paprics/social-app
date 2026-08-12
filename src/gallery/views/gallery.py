# src/gallery/views/gallery.py

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views import View

from gallery.forms import AlbumCreateForm
from gallery.models import UserAlbum
from gallery.selectors.albums import get_gallery_albums
from gallery.selectors.gallery import (
    get_gallery_access_context,
    get_gallery_stats,
    get_gallery_target_user,
)
from gallery.selectors.photos import get_gallery_photos

ALBUMS_PER_PAGE = 12
PHOTOS_PER_PAGE = 20


def get_gallery_state(request, pk):
    target = get_gallery_target_user(user_id=pk)

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

    gallery_stats = get_gallery_stats(
        target=target,
        access=access,
    )

    return target, access, gallery_stats


class GalleryView(View):
    """Display the gallery page shell."""

    template_name = "gallery/gallery.html"

    def get(self, request, pk):
        target, access, gallery_stats = get_gallery_state(
            request,
            pk,
        )

        context = {
            "profile": target.profile,
            "profile_user": target,
            "is_owner": access["is_owner"],
            "gallery_stats": gallery_stats,
            "album_visibility_choices": UserAlbum.Visibility.choices,
            "album_create_form": AlbumCreateForm(),
        }

        return render(
            request,
            self.template_name,
            context,
        )


class GalleryAlbumsView(View):
    """Return one paginated page of gallery albums."""

    template_name = "gallery/partials/_albums_page.html"

    def get(self, request, pk):
        target, access, gallery_stats = get_gallery_state(
            request,
            pk,
        )

        albums = get_gallery_albums(
            target=target,
            access=access,
        )

        paginator = Paginator(
            albums,
            ALBUMS_PER_PAGE,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "profile": target.profile,
                "profile_user": target,
                "is_owner": access["is_owner"],
                "gallery_stats": gallery_stats,
                "all_albums": page_obj.object_list,
                "page_obj": page_obj,
                "gallery_tab": "albums",
            },
        )


class GalleryPhotosView(View):
    """Return one paginated page of gallery photos."""

    template_name = "gallery/partials/_photos_page.html"

    def get(self, request, pk):
        target, access, gallery_stats = get_gallery_state(
            request,
            pk,
        )

        photos = get_gallery_photos(
            target=target,
            access=access,
        )

        paginator = Paginator(
            photos,
            PHOTOS_PER_PAGE,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "profile": target.profile,
                "profile_user": target,
                "is_owner": access["is_owner"],
                "gallery_stats": gallery_stats,
                "all_photos": page_obj.object_list,
                "page_obj": page_obj,
                "gallery_tab": "photos",
            },
        )
