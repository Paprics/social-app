# src/users/views/__init__.py
from .block import *
from .settings import *
from .favorite import *
from .block import *

from .gallery import (
    GalleryView,
    PhotoUploadView,
    AlbumDetailView,
    AlbumSettingsView,
    PhotoDeleteView,
)
from .friendship import (
    FriendRequestSendView,
    FriendRequestCancelView,
    FriendRequestAcceptView,
    FriendRequestDeclineView,
    FriendRemoveView,
)

from .account_center import (
    AccountCenterView,
    AccountCenterIncomingFriendRequestsView,
    AccountCenterOutgoingFriendRequestsView,
    AccountCenterFriendsListView,
    AccountCenterStatisticsView,
    AccountCenterProfileVisitsView,
)

from .profile import (
    ProfileView,
    AvatarModalView,
    AvatarSetView,
    AvatarUploadView,
)

from .profile_explore import (
    ProfileExploreView,
    ProfileExplorePhotosView,
    ProfileExploreAlbumsView,
    ProfileExploreFriendsView,
    ProfileExploreMutualFriendsView,
    ProfileExplorePostsView,
    ProfileExploreVideosView,
)
