# src/gallery/views/__init__.py

from gallery.views.albums import (
    AlbumCreateView,
    AlbumDeleteView,
    AlbumDetailView,
    AlbumSettingsView,
)
from gallery.views.gallery import (
    GalleryAlbumsView,
    GalleryPhotosView,
    GalleryView,
)
from gallery.views.photos import (
    PhotoDeleteView,
    PhotoLightboxDetailView,
    PhotoUploadView,
)

from gallery.views.comments import (
    PhotoCommentCreateView,
    PhotoCommentDeleteView,
    PhotoCommentDetailView,
    PhotoCommentListView,
    PhotoCommentReplyView,
    PhotoCommentUpdateView,
)

__all__ = [
    "AlbumCreateView",
    "AlbumDeleteView",
    "AlbumDetailView",
    "AlbumSettingsView",
    "GalleryAlbumsView",
    "GalleryPhotosView",
    "GalleryView",
    "PhotoDeleteView",
    "PhotoLightboxDetailView",
    "PhotoUploadView",
    "PhotoCommentCreateView",
    "PhotoCommentDeleteView",
    "PhotoCommentDetailView",
    "PhotoCommentListView",
    "PhotoCommentReplyView",
    "PhotoCommentUpdateView",
]
