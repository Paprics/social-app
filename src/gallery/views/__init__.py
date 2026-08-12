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
    PhotoUploadView,
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
    "PhotoUploadView",
]
