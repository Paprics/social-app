# src/gallery/urls.py

from django.urls import path

from gallery.views import (
    AlbumCreateView,
    AlbumDeleteView,
    AlbumDetailView,
    AlbumSettingsView,
    GalleryAlbumsView,
    GalleryPhotosView,
    GalleryView,
    PhotoDeleteView,
    PhotoLightboxDetailView,
    PhotoUploadView,
    PhotoCommentCreateView,
    PhotoCommentDeleteView,
    PhotoCommentDetailView,
    PhotoCommentListView,
    PhotoCommentReplyView,
    PhotoCommentUpdateView,
    PhotoLikesListView,
    PhotoLikeToggleView,
)

app_name = "gallery"

urlpatterns = [
    # Gallery
    path(
        "<int:pk>/gallery/",
        GalleryView.as_view(),
        name="gallery",
    ),
    path(
        "<int:pk>/gallery/albums/",
        GalleryAlbumsView.as_view(),
        name="gallery_albums",
    ),
    path(
        "<int:pk>/gallery/photos/",
        GalleryPhotosView.as_view(),
        name="gallery_photos",
    ),
    # Albums
    path(
        "<int:pk>/gallery/<int:album_pk>/",
        AlbumDetailView.as_view(),
        name="album_detail",
    ),
    path(
        "<int:pk>/gallery/<int:album_pk>/settings/",
        AlbumSettingsView.as_view(),
        name="album_settings",
    ),
    path(
        "<int:pk>/gallery/<int:album_pk>/settings/save/",
        AlbumSettingsView.as_view(),
        name="album_settings_save",
    ),
    path(
        "<int:pk>/gallery/<int:album_pk>/delete/",
        AlbumDeleteView.as_view(),
        name="album_delete",
    ),
    # Photos
    path(
        "<int:pk>/gallery/<int:album_pk>/photos/upload/",
        PhotoUploadView.as_view(),
        name="photo_upload",
    ),
    path(
        "photos/<int:photo_pk>/lightbox/",
        PhotoLightboxDetailView.as_view(),
        name="photo_lightbox_detail",
    ),
    path(
        "photos/<int:photo_pk>/delete/",
        PhotoDeleteView.as_view(),
        name="photo_delete",
    ),
    # Album creation
    path(
        "albums/photos/create/",
        AlbumCreateView.as_view(),
        {"album_type": "photo"},
        name="photo_album_create",
    ),
    path(
        "albums/videos/create/",
        AlbumCreateView.as_view(),
        {"album_type": "video"},
        name="video_album_create",
    ),
    path(
        "photos/<int:photo_pk>/like/",
        PhotoLikeToggleView.as_view(),
        name="photo_like_toggle",
    ),
    path(
        "photos/<int:photo_pk>/likes/",
        PhotoLikesListView.as_view(),
        name="photo_likes_list",
    ),
    # Photo comments
    path(
        "photos/<int:photo_pk>/comments/",
        PhotoCommentListView.as_view(),
        name="photo_comment_list",
    ),
    path(
        "photos/<int:photo_pk>/comments/create/",
        PhotoCommentCreateView.as_view(),
        name="photo_comment_create",
    ),
    path(
        "photos/<int:photo_pk>/comments/<int:comment_id>/",
        PhotoCommentDetailView.as_view(),
        name="photo_comment_detail",
    ),
    path(
        "photos/<int:photo_pk>/comments/<int:comment_id>/reply/",
        PhotoCommentReplyView.as_view(),
        name="photo_comment_reply",
    ),
    path(
        "photos/<int:photo_pk>/comments/<int:comment_id>/update/",
        PhotoCommentUpdateView.as_view(),
        name="photo_comment_update",
    ),
    path(
        "photos/<int:photo_pk>/comments/<int:comment_id>/delete/",
        PhotoCommentDeleteView.as_view(),
        name="photo_comment_delete",
    ),
]
