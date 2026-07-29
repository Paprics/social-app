# src/users/views/__init__.py
from .block import *
from .settings import *

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
)

from .profile import (
    ProfileView,
    AvatarModalView,
    AvatarSetView,
    AvatarUploadView,
)
