# src/posts/urls.py

from django.urls import path

from posts.views.comment import (
    CommentCreateView,
    CommentDeleteView,
    CommentDetailView,
    CommentListView,
    CommentUpdateView,
)
from posts.views.post import (
    CreatePostView,
    DeletePostView,
    PostDetailView,
    UpdatePostView,
    WallPostsView,
)

app_name = "posts"


post_urlpatterns = [
    path(
        "wall/<int:user_id>/",
        WallPostsView.as_view(),
        name="wall_posts",
    ),
    path(
        "wall/<int:user_id>/create/",
        CreatePostView.as_view(),
        name="wall_create",
    ),
    path(
        "<int:post_id>/",
        PostDetailView.as_view(),
        name="detail",
    ),
    path(
        "<int:post_id>/update/",
        UpdatePostView.as_view(),
        name="update",
    ),
    path(
        "<int:post_id>/delete/",
        DeletePostView.as_view(),
        name="delete",
    ),
]


comment_urlpatterns = [
    path(
        "<int:post_id>/comments/",
        CommentListView.as_view(),
        name="comment_list",
    ),
    path(
        "<int:post_id>/comments/create/",
        CommentCreateView.as_view(),
        name="comment_create",
    ),
    path(
        "comments/<int:comment_id>/",
        CommentDetailView.as_view(),
        name="comment_detail",
    ),
    path(
        "comments/<int:comment_id>/update/",
        CommentUpdateView.as_view(),
        name="comment_update",
    ),
    path(
        "comments/<int:comment_id>/delete/",
        CommentDeleteView.as_view(),
        name="comment_delete",
    ),
]


urlpatterns = [
    *post_urlpatterns,
    *comment_urlpatterns,
]
