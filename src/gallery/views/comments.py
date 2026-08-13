# src/gallery/views/comments.py

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views import View

from gallery.selectors.comments import (
    get_photo_comment,
    get_photo_comments,
    get_photo_comments_count,
)
from gallery.selectors.gallery import get_gallery_access_context
from gallery.selectors.photos import (
    get_photo_for_view,
    get_photo_target_user,
)
from gallery.services.photo_comment_access import PhotoCommentAccessService
from posts.forms.comment import CommentForm
from posts.services.comment import CommentService
from users.services.user_block import UserBlockService

PAGE_SIZE = 10


def _get_photo_state(*, request, photo_pk):
    """
    Return photo and comment access service for the current viewer.
    """

    target = get_photo_target_user(
        photo_id=photo_pk,
    )

    if target is None:
        raise Http404

    gallery_state = get_gallery_access_context(
        viewer=request.user,
        target=target,
    )

    if not gallery_state["can_view_profile"]:
        raise Http404

    if not gallery_state["can_view_gallery"]:
        raise PermissionDenied

    photo = get_photo_for_view(
        target=target,
        photo_id=photo_pk,
        access=gallery_state,
    )

    if photo is None:
        raise Http404

    is_blocked = False

    if request.user.is_authenticated and request.user.pk != target.pk:
        is_blocked = UserBlockService.is_blocked(
            request.user,
            target,
        )

    comment_access = PhotoCommentAccessService(
        viewer=request.user,
        target=target,
        gallery_access=gallery_state["gallery_access"],
        is_friend=gallery_state["is_friend"],
        is_blocked=is_blocked,
        can_view_profile=gallery_state["can_view_profile"],
    )

    if not comment_access.can_view_comments(photo):
        raise PermissionDenied

    return photo, comment_access


def _build_comment_item(*, access, comment):
    """Build rendering permissions for one comment."""

    replies = []

    for reply in getattr(comment, "loaded_replies", []):
        replies.append(
            {
                "comment": reply,
                "can_edit": access.can_edit_comment(reply),
                "can_delete": access.can_delete_comment(reply),
                "can_reply": False,
                "replies": [],
            }
        )

    can_reply = comment.parent_id is None and access.can_reply_to_comment(
        photo=comment.photo,
        comment=comment,
    )

    return {
        "comment": comment,
        "can_edit": access.can_edit_comment(comment),
        "can_delete": access.can_delete_comment(comment),
        "can_reply": can_reply,
        "replies": replies,
    }


def _get_render_item(*, photo, comment_id, access):
    """
    Return one comment prepared for rendering.

    Root comments are loaded together with their replies.
    """

    comment = get_photo_comment(
        photo=photo,
        comment_id=comment_id,
    )

    if comment.parent_id is None:
        comment = get_photo_comments(photo=photo).filter(pk=comment.pk).first()

        if comment is None:
            raise Http404

    return _build_comment_item(
        access=access,
        comment=comment,
    )


class PhotoCommentListView(View):
    """Render photo comments in pages of ten root comments."""

    def get(self, request, photo_pk):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        comments = get_photo_comments(
            photo=photo,
        )

        snapshot_raw = request.GET.get("snapshot")

        if snapshot_raw:
            try:
                snapshot = int(snapshot_raw)
            except (TypeError, ValueError):
                raise Http404 from None
        else:
            snapshot = comments.order_by("-id").values_list("id", flat=True).first() or 0

        if snapshot:
            comments = comments.filter(
                id__lte=snapshot,
            )
        else:
            comments = comments.none()

        paginator = Paginator(
            comments,
            PAGE_SIZE,
        )

        page_obj = paginator.get_page(
            request.GET.get("page", 1),
        )

        comment_items = [
            _build_comment_item(
                access=access,
                comment=comment,
            )
            for comment in page_obj.object_list
        ]

        context = {
            "photo": photo,
            "comment_items": comment_items,
            "total_count": get_photo_comments_count(
                photo=photo,
            ),
            "can_comment": access.can_comment_on_photo(photo),
            "comment_form": CommentForm(),
            "snapshot": snapshot,
            "next_page": (page_obj.next_page_number() if page_obj.has_next() else None),
        }

        if request.GET.get("page"):
            return render(
                request,
                "gallery/partials/comments/_page.html",
                context,
            )

        return render(
            request,
            "gallery/partials/comments/_list.html",
            context,
        )


class PhotoCommentDetailView(View):
    """Render one photo comment."""

    def get(self, request, photo_pk, comment_id):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        item = _get_render_item(
            photo=photo,
            comment_id=comment_id,
            access=access,
        )

        return render(
            request,
            "gallery/partials/comments/_comment.html",
            {
                "photo": photo,
                "item": item,
            },
        )


class PhotoCommentCreateView(View):
    """Create a root comment on a photo."""

    def post(self, request, photo_pk):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        if not access.can_comment_on_photo(photo):
            raise PermissionDenied

        form = CommentForm(
            request.POST,
        )

        if not form.is_valid():
            return render(
                request,
                "gallery/partials/comments/_form.html",
                {
                    "photo": photo,
                    "comment_form": form,
                },
            )

        try:
            comment = CommentService.create(
                author=request.user,
                content=form.cleaned_data["content"],
                photo=photo,
            )
        except ValidationError as error:
            form.add_error(
                None,
                error,
            )

            return render(
                request,
                "gallery/partials/comments/_form.html",
                {
                    "photo": photo,
                    "comment_form": form,
                },
            )

        item = _build_comment_item(
            access=access,
            comment=comment,
        )

        return render(
            request,
            "gallery/partials/comments/_create_result.html",
            {
                "photo": photo,
                "item": item,
                "comment_form": CommentForm(),
                "total_count": get_photo_comments_count(
                    photo=photo,
                ),
            },
        )


class PhotoCommentReplyView(View):
    """Create one reply to a root photo comment."""

    def get(self, request, photo_pk, comment_id):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        parent = get_photo_comment(
            photo=photo,
            comment_id=comment_id,
        )

        if not access.can_reply_to_comment(
            photo=photo,
            comment=parent,
        ):
            raise PermissionDenied

        return render(
            request,
            "gallery/partials/comments/_reply_form.html",
            {
                "photo": photo,
                "parent": parent,
                "comment_form": CommentForm(),
            },
        )

    def post(self, request, photo_pk, comment_id):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        parent = get_photo_comment(
            photo=photo,
            comment_id=comment_id,
        )

        if not access.can_reply_to_comment(
            photo=photo,
            comment=parent,
        ):
            raise PermissionDenied

        form = CommentForm(
            request.POST,
        )

        if not form.is_valid():
            return render(
                request,
                "gallery/partials/comments/_reply_form.html",
                {
                    "photo": photo,
                    "parent": parent,
                    "comment_form": form,
                },
            )

        try:
            comment = CommentService.create(
                author=request.user,
                content=form.cleaned_data["content"],
                photo=photo,
                parent=parent,
            )
        except ValidationError as error:
            form.add_error(
                None,
                error,
            )

            return render(
                request,
                "gallery/partials/comments/_reply_form.html",
                {
                    "photo": photo,
                    "parent": parent,
                    "comment_form": form,
                },
            )

        item = _build_comment_item(
            access=access,
            comment=comment,
        )

        return render(
            request,
            "gallery/partials/comments/_reply_result.html",
            {
                "photo": photo,
                "parent": parent,
                "item": item,
                "total_count": get_photo_comments_count(
                    photo=photo,
                ),
            },
        )


class PhotoCommentUpdateView(View):
    """Edit an existing photo comment."""

    def get(self, request, photo_pk, comment_id):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        comment = get_photo_comment(
            photo=photo,
            comment_id=comment_id,
        )

        if not access.can_edit_comment(comment):
            raise PermissionDenied

        return render(
            request,
            "gallery/partials/comments/_edit_form.html",
            {
                "photo": photo,
                "comment": comment,
                "comment_form": CommentForm(
                    initial={
                        "content": comment.content,
                    }
                ),
            },
        )

    def post(self, request, photo_pk, comment_id):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        comment = get_photo_comment(
            photo=photo,
            comment_id=comment_id,
        )

        if not access.can_edit_comment(comment):
            raise PermissionDenied

        form = CommentForm(
            request.POST,
        )

        if not form.is_valid():
            return render(
                request,
                "gallery/partials/comments/_edit_form.html",
                {
                    "photo": photo,
                    "comment": comment,
                    "comment_form": form,
                },
            )

        try:
            CommentService.update(
                comment=comment,
                content=form.cleaned_data["content"],
            )
        except ValidationError as error:
            form.add_error(
                None,
                error,
            )

            return render(
                request,
                "gallery/partials/comments/_edit_form.html",
                {
                    "photo": photo,
                    "comment": comment,
                    "comment_form": form,
                },
            )

        item = _get_render_item(
            photo=photo,
            comment_id=comment.pk,
            access=access,
        )

        return render(
            request,
            "gallery/partials/comments/_comment.html",
            {
                "photo": photo,
                "item": item,
            },
        )


class PhotoCommentDeleteView(View):
    """Delete a photo comment owned by the current user."""

    def post(self, request, photo_pk, comment_id):
        photo, access = _get_photo_state(
            request=request,
            photo_pk=photo_pk,
        )

        comment = get_photo_comment(
            photo=photo,
            comment_id=comment_id,
        )

        if not access.can_delete_comment(comment):
            raise PermissionDenied

        CommentService.delete(
            comment=comment,
        )

        return render(
            request,
            "gallery/partials/comments/_delete_result.html",
            {
                "total_count": get_photo_comments_count(
                    photo=photo,
                ),
            },
        )
