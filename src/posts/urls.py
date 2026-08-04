from django.urls import path

# from posts.views.comment import (
#     create_comment,
#     delete_comment,
#     update_comment,
# )

from posts.views.post import (
    CreatePostView,
    DeletePostView,
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

# comment_urlpatterns = [
#     path("<int:post_id>/comments/create/", create_comment, name="comment-create"),
#     path("comments/<int:comment_id>/update/", update_comment, name="comment-update"),
#     path("comments/<int:comment_id>/delete/", delete_comment, name="comment-delete"),
# ]

urlpatterns = [
    *post_urlpatterns,
    # *comment_urlpatterns,
]
