from django.views.generic import TemplateView, DetailView
from users.models import Photo, UserAlbum


class PhotoAlbumListView(TemplateView):
    template_name = "users\photo_albums.html"


class PhotoAlbumDetailView(DetailView):
    model = UserAlbum
    template_name = "users/photo_album_detail.html"
