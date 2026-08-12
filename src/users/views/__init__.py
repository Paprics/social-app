# src/users/views/__init__.py
from .block import *
from .settings import *
from .favorite import *
from .block import *

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

from users.views.avatar import (
    AvatarModalView,
    AvatarRemoveView,
    AvatarSetView,
    AvatarUploadView,
    AvatarPhotosView,
)
