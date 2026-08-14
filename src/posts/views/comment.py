# src/posts/views/comment.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views import View

from posts.forms.comment import CommentForm
from posts.selectors.comment import (
    get_comment,
    get_post_comments,
)
from posts.selectors.post import get_post
from posts.services.access.comment import CommentAccessService
from posts.services.comment import CommentService
from users.selectors.user_block import get_block_state
from users.services.access import ProfileAccessService
from users.services.friendship_service import FriendshipService


def _build_comment_access(*, viewer, target):
    """Build comment access rules for viewer and wall owner."""

    if not viewer.is_authenticated or viewer == target:
        is_friend = False
        block_state = {
            "is_blocked": False,
            "target_has_blocked": False,
        }
    else:
        block_state = get_block_state(
            viewer,
            target,
        )

        is_friend = (
            False
            if block_state["is_blocked"]
            else FriendshipService.are_friends(
                viewer,
                target,
            )
        )

    profile_access = ProfileAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=block_state["is_blocked"],
        target_has_blocked=block_state["target_has_blocked"],
    )

    return CommentAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=block_state["is_blocked"],
        can_view_profile=profile_access.can_view_profile(),
    )


def _get_comment_permissions(*, access, comment):
    """Return UI permissions for one comment."""

    return {
        "can_edit": access.can_edit_comment(comment),
        "can_delete": access.can_delete_comment(comment),
    }


def _render_comment(request, *, comment, access):
    """Render one complete comment partial."""

    return render(
        request,
        "posts/partials/comment.html",
        {
            "comment": comment,
            "comment_permissions": _get_comment_permissions(
                access=access,
                comment=comment,
            ),
        },
    )


def _render_edit_form(request, *, comment, form):
    """Render comment editing form."""

    return render(
        request,
        "posts/partials/comment_edit_form.html",
        {
            "comment": comment,
            "form": form,
        },
    )


class CommentListView(LoginRequiredMixin, View):
    """Return one paginated page of comments."""

    PAGE_SIZE = 10

    def get(self, request, post_id):
        post = get_post(
            post_id=post_id,
        )

        access = _build_comment_access(
            viewer=request.user,
            target=post.owner,
        )

        if not access.can_view_comments(post):
            raise PermissionDenied

        comments_queryset = get_post_comments(
            post=post,
        )

        paginator = Paginator(
            comments_queryset,
            self.PAGE_SIZE,
        )

        page_obj = paginator.get_page(request.GET.get("page", 1))

        comment_items = [
            {
                "comment": comment,
                "permissions": _get_comment_permissions(
                    access=access,
                    comment=comment,
                ),
            }
            for comment in page_obj.object_list
        ]

        context = {
            "post": post,
            "comment_items": comment_items,
            "has_next": page_obj.has_next(),
            "next_page": (page_obj.next_page_number() if page_obj.has_next() else None),
            "show_empty_state": page_obj.number == 1,
            "can_comment": access.can_comment_on_post(post),
        }

        if page_obj.number == 1:
            template_name = "posts/partials/comment_list.html"
        else:
            template_name = "posts/partials/comment_page.html"

        return render(
            request,
            template_name,
            context,
        )


class CommentDetailView(LoginRequiredMixin, View):
    """Render one comment."""

    def get(self, request, comment_id):
        comment = get_comment(
            comment_id=comment_id,
        )

        access = _build_comment_access(
            viewer=request.user,
            target=comment.post.owner,
        )

        if not access.can_view_comments(comment.post):
            raise PermissionDenied

        return _render_comment(
            request,
            comment=comment,
            access=access,
        )


class CommentCreateView(LoginRequiredMixin, View):
    """Create a comment on a post."""

    def post(self, request, post_id):
        post = get_post(
            post_id=post_id,
        )

        access = _build_comment_access(
            viewer=request.user,
            target=post.owner,
        )

        if not access.can_comment_on_post(post):
            raise PermissionDenied

        form = CommentForm(
            request.POST,
        )

        if not form.is_valid():
            errors = form.errors.get("content")

            message = errors[0] if errors else "Invalid comment."

            return HttpResponseBadRequest(
                message,
            )

        comment = CommentService.create(
            post=post,
            author=request.user,
            content=form.cleaned_data["content"],
        )

        return _render_comment(
            request,
            comment=comment,
            access=access,
        )


class CommentUpdateView(LoginRequiredMixin, View):
    """Edit an existing comment."""

    def get(self, request, comment_id):
        comment = get_comment(
            comment_id=comment_id,
        )

        access = _build_comment_access(
            viewer=request.user,
            target=comment.post.owner,
        )

        if not access.can_edit_comment(comment):
            raise PermissionDenied

        form = CommentForm(
            initial={
                "content": comment.content,
            }
        )

        return _render_edit_form(
            request,
            comment=comment,
            form=form,
        )

    def post(self, request, comment_id):
        comment = get_comment(
            comment_id=comment_id,
        )

        access = _build_comment_access(
            viewer=request.user,
            target=comment.post.owner,
        )

        if not access.can_edit_comment(comment):
            raise PermissionDenied

        form = CommentForm(
            request.POST,
        )

        if not form.is_valid():
            return _render_edit_form(
                request,
                comment=comment,
                form=form,
            )

        CommentService.update(
            comment=comment,
            content=form.cleaned_data["content"],
        )

        return _render_comment(
            request,
            comment=comment,
            access=access,
        )


class CommentDeleteView(LoginRequiredMixin, View):
    """Delete an existing comment."""

    def delete(self, request, comment_id):
        comment = get_comment(
            comment_id=comment_id,
        )

        access = _build_comment_access(
            viewer=request.user,
            target=comment.post.owner,
        )

        if not access.can_delete_comment(comment):
            raise PermissionDenied

        CommentService.delete(
            comment=comment,
        )

        return HttpResponse("")
