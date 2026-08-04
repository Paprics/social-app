from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from posts.forms import PostForm
from posts.services import PostService

from users.models import Profile
from posts.models import Post


class WallPostsView(LoginRequiredMixin, View):
    """Отображает список записей на стене."""

    template_name = "posts/partials/post_list.html"

    PAGE_SIZE = 10

    def get(self, request, user_id):

        page_number = int(request.GET.get("page", 1))

        profile = get_object_or_404(
            Profile,
            user_id=user_id,
        )

        posts_queryset = (
            Post.objects.filter(owner=profile.user)
            .select_related(
                "author",
                "author__profile",
                "author__profile__avatar_photo",
            )
            .order_by("-id")
        )

        paginator = Paginator(
            posts_queryset,
            self.PAGE_SIZE,
        )

        page_obj = paginator.get_page(page_number)

        context = {
            "profile_user": profile.user,
            "posts": page_obj,
            "has_next": page_obj.has_next(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
        }

        return render(
            request,
            self.template_name,
            context,
        )


class DeletePostView(LoginRequiredMixin, View):
    """Удаление поста."""

    def delete(self, request, post_id):

        post = get_object_or_404(
            Post,
            pk=post_id,
        )

        if post.author != request.user:
            raise PermissionDenied

        PostService.delete_post(post)

        return HttpResponse("")


class CreatePostView(LoginRequiredMixin, View):
    """Создает новую запись на стене."""

    def post(self, request, user_id):

        profile = get_object_or_404(
            Profile,
            user_id=user_id,
        )

        form = PostForm(request.POST)

        if not form.is_valid():
            # Вернуть форму с ошибками
            raise NotImplementedError

        post = PostService.create(
            owner=profile.user,
            author=request.user,
            content=form.cleaned_data["content"],
        )

        context = {
            "post": post,
            "profile_user": profile.user,
        }

        return render(
            request,
            "posts/partials/post.html",
            context,
        )


class UpdatePostView(LoginRequiredMixin, View):
    """Редактирование поста."""

    def get(self, request, post_id):

        post = get_object_or_404(
            Post,
            pk=post_id,
            author=request.user,
        )

        form = PostForm(
            initial={
                "content": post.content,
            }
        )

        return render(
            request,
            "posts/partials/post_edit_form.html",
            {
                "post": post,
                "form": form,
            },
        )

    def post(self, request, post_id):

        print("=" * 50)
        print("UPDATE POST")
        print("POST ID:", post_id)
        print("METHOD:", request.method)
        print("POST DATA:", request.POST)
        print("CONTENT:", request.POST.get("content"))
        print("=" * 50)

        post = get_object_or_404(
            Post,
            pk=post_id,
            author=request.user,
        )

        PostService.update_post(
            post,
            content=request.POST.get("content"),
        )

        return render(
            request,
            "posts/partials/post.html",
            {
                "post": post,
            },
        )
