# src/users/views/profile_explore.py

"""Views for the profile Explore shell and its lazy-loaded sections."""

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from gallery.selectors.gallery import (
    get_gallery_access_context,
    get_gallery_target_user,
)
from users.services.profile_context import ProfileContextBuilder
from gallery.selectors.albums import get_gallery_albums
from gallery.selectors.photos import get_gallery_photos
from users.services.access import ProfileAccessService
from users.services.friendship_service import FriendshipService
from users.services.profile_context.target import get_profile_target
from posts.selectors.post import get_wall_owner, get_wall_posts
from posts.services.access.context import (
    build_post_access,
    get_post_permissions,
)
from users.selectors.friendship import (
    get_friends,
    get_mutual_friends,
)


class ProfileExploreView(TemplateView):
    """Render the lightweight profile Explore shell."""

    template_name = "users/profile_explore.html"

    def get_context_data(self, **kwargs):
        """Build Explore context through ProfileContextBuilder."""

        context = super().get_context_data(**kwargs)

        explore_context = ProfileContextBuilder.build_explore(
            self.request,
            self.kwargs["pk"],
        )

        context.update(explore_context)

        return context


class ProfileExplorePhotosView(View):
    """Load a paginated collection of accessible profile photos."""

    template_name = "users/partials/explore/photos.html"
    paginate_by = settings.GALLERY_PHOTOS_PER_PAGE

    def get(self, request, pk):
        """Return one photos page for the Explore interface."""

        target = get_gallery_target_user(
            user_id=pk,
        )

        if target is None:
            raise Http404

        access = get_gallery_access_context(
            viewer=request.user,
            target=target,
        )

        if not access["can_view_profile"]:
            raise Http404

        photos_queryset = get_gallery_photos(
            target=target,
            access=access,
        )

        paginator = Paginator(
            photos_queryset,
            self.paginate_by,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "target_user": target,
                "is_owner": access["is_owner"],
                "can_view_gallery": access["can_view_gallery"],
                "photos": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
            },
        )


class ProfileExploreAlbumsView(View):
    """Load a paginated collection of accessible profile albums."""

    template_name = "users/partials/explore/albums.html"
    paginate_by = settings.GALLERY_ALBUMS_PER_PAGE

    def get(self, request, pk):
        """Return one albums page for the Explore interface."""

        target = get_gallery_target_user(
            user_id=pk,
        )

        if target is None:
            raise Http404

        access = get_gallery_access_context(
            viewer=request.user,
            target=target,
        )

        if not access["can_view_profile"]:
            raise Http404

        albums_queryset = get_gallery_albums(
            target=target,
            access=access,
        )

        paginator = Paginator(
            albums_queryset,
            self.paginate_by,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "target_user": target,
                "is_owner": access["is_owner"],
                "can_view_gallery": access["can_view_gallery"],
                "albums": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
            },
        )


class ProfileExploreFriendsView(View):
    """Load a paginated collection of accessible profile friendships."""

    template_name = "users/partials/explore/friends.html"
    paginate_by = settings.PROFILE_EXPLORE_FRIENDS_PER_PAGE

    def get(self, request, pk):
        """Return one friends page for the Explore interface."""

        target = get_profile_target(pk)

        relation = FriendshipService.get_relation(
            request.user,
            target,
        )

        access_service = ProfileAccessService(
            viewer=request.user,
            target=target,
            is_friend=relation["is_friend"],
        )

        if not access_service.can_view_profile():
            raise Http404

        can_view_friends = access_service.can_view_friends()

        if not can_view_friends:
            return render(
                request,
                self.template_name,
                {
                    "target_user": target,
                    "is_owner": request.user == target,
                    "can_view_friends": False,
                    "friends": [],
                    "friendships": [],
                    "page_obj": None,
                    "paginator": None,
                },
            )

        friendships_queryset = get_friends(
            target,
        )

        paginator = Paginator(
            friendships_queryset,
            self.paginate_by,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        friends = [
            (friendship.to_user if friendship.from_user_id == target.pk else friendship.from_user)
            for friendship in page_obj.object_list
        ]

        return render(
            request,
            self.template_name,
            {
                "target_user": target,
                "is_owner": request.user == target,
                "can_view_friends": True,
                "friends": friends,
                "friendships": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
            },
        )


class ProfileExploreMutualFriendsView(View):
    """Load a paginated collection of mutual friends."""

    template_name = "users/partials/explore/mutual_friends.html"
    paginate_by = settings.PROFILE_EXPLORE_FRIENDS_PER_PAGE

    def get(self, request, pk):
        """Return one mutual friends page for the Explore interface."""

        target = get_profile_target(pk)

        relation = FriendshipService.get_relation(
            request.user,
            target,
        )

        access_service = ProfileAccessService(
            viewer=request.user,
            target=target,
            is_friend=relation["is_friend"],
        )

        if not access_service.can_view_profile():
            raise Http404

        can_view_mutual_friends = (
            request.user.is_authenticated and request.user != target and access_service.can_view_friends()
        )

        if not can_view_mutual_friends:
            return render(
                request,
                self.template_name,
                {
                    "target_user": target,
                    "is_owner": request.user == target,
                    "can_view_mutual_friends": False,
                    "mutual_friends": [],
                    "page_obj": None,
                    "paginator": None,
                },
            )

        mutual_friends_queryset = get_mutual_friends(
            request.user,
            target,
        )

        paginator = Paginator(
            mutual_friends_queryset,
            self.paginate_by,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        return render(
            request,
            self.template_name,
            {
                "target_user": target,
                "is_owner": False,
                "can_view_mutual_friends": True,
                "mutual_friends": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
            },
        )


class ProfileExplorePostsView(View):
    """Load a paginated collection of accessible wall posts."""

    template_name = "users/partials/explore/posts.html"
    paginate_by = settings.PROFILE_EXPLORE_POSTS_PER_PAGE

    def get(self, request, pk):
        """Return one posts page for the Explore interface."""

        target = get_wall_owner(
            user_id=pk,
        )

        access = build_post_access(
            viewer=request.user,
            target=target,
        )

        if not access.can_view_profile:
            raise Http404

        can_view_wall = access.can_view_wall()

        if not can_view_wall:
            return render(
                request,
                self.template_name,
                {
                    "target_user": target,
                    "is_owner": request.user == target,
                    "can_view_wall": False,
                    "posts": [],
                    "post_items": [],
                    "page_obj": None,
                    "paginator": None,
                },
            )

        posts_queryset = get_wall_posts(
            owner=target,
        )

        paginator = Paginator(
            posts_queryset,
            self.paginate_by,
        )

        page_obj = paginator.get_page(
            request.GET.get("page"),
        )

        posts = page_obj.object_list

        post_items = [
            {
                "post": post,
                "permissions": get_post_permissions(
                    access=access,
                    post=post,
                ),
            }
            for post in posts
        ]

        return render(
            request,
            self.template_name,
            {
                "target_user": target,
                "is_owner": request.user == target,
                "can_view_wall": True,
                "posts": posts,
                "post_items": post_items,
                "page_obj": page_obj,
                "paginator": paginator,
            },
        )


class ProfileExploreVideosView(View):
    """Load profile videos for Explore."""
