# src/posts/views/post.py

"""Views for displaying, creating, updating, and deleting wall posts."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from posts.forms.post import PostForm
from posts.selectors.post import (
    get_post,
    get_wall_owner,
    get_wall_posts,
)
from posts.services.access.context import (
    build_post_access,
    get_post_permissions,
)
from posts.services.media import (
    PostMediaLimitError,
    PostMediaPermissionError,
    PostMediaService,
)
from posts.services.post import PostService


def _render_post(request, *, post, access):
    """Render one complete post partial."""

    return render(
        request,
        "posts/partials/post.html",
        {
            "post": post,
            "profile_user": post.owner,
            "post_permissions": get_post_permissions(
                access=access,
                post=post,
            ),
        },
    )


def _render_edit_form(request, *, post, form):
    """Render the post editing partial."""

    return render(
        request,
        "posts/partials/post_edit_form.html",
        {
            "post": post,
            "form": form,
        },
    )


def _json_error(message):
    """Return the standard create-post error response."""

    return JsonResponse(
        {
            "error": message,
        },
        status=400,
    )


def _form_error_message(form):
    """Return the first human-readable form validation error."""

    for errors in form.errors.as_data().values():
        if not errors:
            continue

        error = errors[0]

        if error.messages:
            return error.messages[0]

    return "Invalid post."


def _exception_error_message(error):
    """Return a readable business or validation error."""

    if isinstance(error, ValidationError) and error.messages:
        return error.messages[0]

    return str(error)


class WallPostsView(LoginRequiredMixin, View):
    """Display one paginated page of wall posts."""

    raise_exception = True
    template_name = "posts/partials/post_list.html"
    PAGE_SIZE = 10

    def get(self, request, user_id):
        target = get_wall_owner(
            user_id=user_id,
        )

        access = build_post_access(
            viewer=request.user,
            target=target,
        )

        if not access.can_view_wall():
            raise PermissionDenied

        posts_queryset = get_wall_posts(
            owner=target,
        )

        paginator = Paginator(
            posts_queryset,
            self.PAGE_SIZE,
        )

        page_obj = paginator.get_page(
            request.GET.get("page", 1),
        )

        post_items = [
            {
                "post": post,
                "permissions": get_post_permissions(
                    access=access,
                    post=post,
                ),
            }
            for post in page_obj.object_list
        ]

        return render(
            request,
            self.template_name,
            {
                "profile_user": target,
                "posts": page_obj,
                "has_next": page_obj.has_next(),
                "next_page": (page_obj.next_page_number() if page_obj.has_next() else None),
                "post_items": post_items,
            },
        )


class PostDetailView(LoginRequiredMixin, View):
    """Render one wall post."""

    def get(self, request, post_id):
        post = get_post(
            post_id=post_id,
        )

        access = build_post_access(
            viewer=request.user,
            target=post.owner,
        )

        if not access.can_view_post(post):
            raise PermissionDenied

        return _render_post(
            request,
            post=post,
            access=access,
        )


class CreatePostView(LoginRequiredMixin, View):
    """Create a new post on a user's wall."""

    def post(self, request, user_id):
        """Create a new wall post with optional image attachments."""

        target = get_wall_owner(
            user_id=user_id,
        )

        access = build_post_access(
            viewer=request.user,
            target=target,
        )

        if not access.can_post_on_wall():
            raise PermissionDenied

        photos = request.FILES.getlist("photos")

        # Media uploads are temporarily staff-only.
        if photos and not request.user.is_staff:
            raise PermissionDenied

        form = PostForm(
            request.POST,
            request.FILES,
        )

        if not form.is_valid():
            return _json_error(
                _form_error_message(form),
            )

        content = form.cleaned_data["content"]

        # A post must contain text, images, or both.
        if not content and not photos:
            return _json_error(
                "Post cannot be empty.",
            )

        try:
            with transaction.atomic():
                post = PostService.create(
                    owner=target,
                    author=request.user,
                    content=content,
                )

                if photos:
                    PostMediaService.upload_files(
                        post=post,
                        actor=request.user,
                        files=photos,
                    )

        except (
            PostMediaPermissionError,
            PostMediaLimitError,
            ValidationError,
        ) as error:
            return _json_error(
                _exception_error_message(error),
            )

        post = get_post(
            post_id=post.pk,
        )

        return _render_post(
            request,
            post=post,
            access=access,
        )


class UpdatePostView(LoginRequiredMixin, View):
    """Edit the text of an existing wall post."""

    def get(self, request, post_id):
        """Render the post editing form."""

        post = get_post(
            post_id=post_id,
        )

        access = build_post_access(
            viewer=request.user,
            target=post.owner,
        )

        if not access.can_edit_post(post):
            raise PermissionDenied

        form = PostForm(
            initial={
                "content": post.content,
            }
        )

        return _render_edit_form(
            request,
            post=post,
            form=form,
        )

    def post(self, request, post_id):
        """Update only the text of an existing post."""

        post = get_post(
            post_id=post_id,
        )

        access = build_post_access(
            viewer=request.user,
            target=post.owner,
        )

        if not access.can_edit_post(post):
            raise PermissionDenied

        form = PostForm(
            request.POST,
        )

        if not form.is_valid():
            return _render_edit_form(
                request,
                post=post,
                form=form,
            )

        content = form.cleaned_data["content"]

        if not content:
            content = post.content

        post = PostService.update(
            post=post,
            content=content,
        )

        post = get_post(
            post_id=post.pk,
        )

        return _render_post(
            request,
            post=post,
            access=access,
        )


class DeletePostView(LoginRequiredMixin, View):
    """Delete an existing wall post."""

    def delete(self, request, post_id):
        post = get_post(
            post_id=post_id,
        )

        access = build_post_access(
            viewer=request.user,
            target=post.owner,
        )

        if not access.can_delete_post(post):
            raise PermissionDenied

        PostService.delete_post(
            post,
        )

        return HttpResponse("")
