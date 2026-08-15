# src/users/urls.py
from django.urls import path

from users.views import (
    ProfileView,
    SettingsAccountView,
    SettingsCommunicationView,
    SettingsPageView,
    SettingsPremiumFeaturesView,
    SettingsPrivacyView,
    SettingsProfileView,
    SensitiveContentToggleView,
    #
    FriendRequestSendView,
    FriendRequestCancelView,
    FriendRequestAcceptView,
    FriendRequestDeclineView,
    FriendRemoveView,
    #
    AccountCenterView,
    AccountCenterIncomingFriendRequestsView,
    AccountCenterOutgoingFriendRequestsView,
    AccountCenterFriendsListView,
    AccountCenterStatisticsView,
    AccountCenterProfileVisitsView,
    #
    AvatarModalView,
    AvatarPhotosView,
    AvatarRemoveView,
    AvatarSetView,
    AvatarUploadView,
    #
    PhotoFavoriteToggleView,
    UserFavoriteToggleView,
    #
    UserBlockCreateView,
    UserBlockDeleteView,
    #
    ProfileExploreView,
    ProfileExplorePhotosView,
    ProfileExploreAlbumsView,
    ProfileExploreFriendsView,
    ProfileExploreMutualFriendsView,
    ProfileExplorePostsView,
    ProfileExploreVideosView,
)
from users.views.account_center import (
    AccountCenterBlacklistListView,
    AccountCenterFavoritePhotosView,
    AccountCenterFavoriteProfilesView,
    AccountCenterLikedPhotosView,
)

app_name = "users"

core_urlpatterns = [
    path("<int:pk>/", ProfileView.as_view(), name="profile"),
    path("settings/", SettingsPageView.as_view(), name="settings"),
]

settings_urlpatterns = [
    path("settings/account/", SettingsAccountView.as_view(), name="account"),
    path("settings/profile/", SettingsProfileView.as_view(), name="settings_profile"),
    path("settings/privacy/", SettingsPrivacyView.as_view(), name="privacy"),
    path("settings/communication/", SettingsCommunicationView.as_view(), name="communication"),
    path("settings/premium-features/", SettingsPremiumFeaturesView.as_view(), name="premium_features"),
    path(
        "settings/preferences/sensitive-content/",
        SensitiveContentToggleView.as_view(),
        name="toggle_sensitive_content",
    ),
]

friendship_urlpatterns = [
    path("<int:pk>/friend-request/send/", FriendRequestSendView.as_view(), name="friend_request_send"),
    path("<int:pk>/friend-request/cancel/", FriendRequestCancelView.as_view(), name="friend_request_cancel"),
    path("<int:pk>/friend-request/accept/", FriendRequestAcceptView.as_view(), name="friend_request_accept"),
    path("<int:pk>/friend-request/decline/", FriendRequestDeclineView.as_view(), name="friend_request_decline"),
    path("<int:pk>/friends/remove/", FriendRemoveView.as_view(), name="friend_remove"),
]

account_center_urlpatterns = [
    path("account-center/", AccountCenterView.as_view(), name="account_center"),
    path(
        "account-center/friends/incoming/",
        AccountCenterIncomingFriendRequestsView.as_view(),
        name="account_center_friends_incoming",
    ),
    path(
        "account-center/friends/outgoing/",
        AccountCenterOutgoingFriendRequestsView.as_view(),
        name="account_center_friends_outgoing",
    ),
    path(
        "account-center/friends/list/",
        AccountCenterFriendsListView.as_view(),
        name="account_center_friends_list",
    ),
    path(
        "account-center/blacklist/list/",
        AccountCenterBlacklistListView.as_view(),
        name="account_center_blacklist_list",
    ),
    path(
        "account-center/statistics/",
        AccountCenterStatisticsView.as_view(),
        name="account_center_statistics",
    ),
    path(
        "account-center/profile-visits/",
        AccountCenterProfileVisitsView.as_view(),
        name="account_center_profile_visits",
    ),
    path(
        "account-center/favorites/photos/",
        AccountCenterFavoritePhotosView.as_view(),
        name="account_center_favorite_photos",
    ),
    path(
        "account-center/favorites/profiles/",
        AccountCenterFavoriteProfilesView.as_view(),
        name="account_center_favorite_profiles",
    ),
    path(
        "account-center/likes/photos/",
        AccountCenterLikedPhotosView.as_view(),
        name="account_center_liked_photos",
    ),
]

avatar_urlpatterns = [
    path(
        "profile/avatar/",
        AvatarModalView.as_view(),
        name="avatar_modal",
    ),
    path(
        "profile/avatar/set/",
        AvatarSetView.as_view(),
        name="avatar_set",
    ),
    path(
        "profile/avatar/upload/",
        AvatarUploadView.as_view(),
        name="avatar_upload",
    ),
    path(
        "profile/avatar/remove/",
        AvatarRemoveView.as_view(),
        name="avatar_remove",
    ),
    path(
        "profile/avatar/photos/",
        AvatarPhotosView.as_view(),
        name="avatar_photos",
    ),
]

favorite_urlpatterns = [
    path(
        "users/<int:pk>/favorite/toggle/",
        UserFavoriteToggleView.as_view(),
        name="user_favorite_toggle",
    ),
    path(
        "photos/<int:pk>/favorite/toggle/",
        PhotoFavoriteToggleView.as_view(),
        name="photo_favorite_toggle",
    ),
]

block_urlpatterns = [
    path("<int:pk>/block/", UserBlockCreateView.as_view(), name="block"),
    path("<int:pk>/unblock/", UserBlockDeleteView.as_view(), name="unblock"),
]

explore_urlpatterns = [
    path("<int:pk>/explore/", ProfileExploreView.as_view(), name="profile_explore"),
    path("<int:pk>/explore/photos/", ProfileExplorePhotosView.as_view(), name="profile_explore_photos"),
    path("<int:pk>/explore/albums/", ProfileExploreAlbumsView.as_view(), name="profile_explore_albums"),
    path("<int:pk>/explore/friends/", ProfileExploreFriendsView.as_view(), name="profile_explore_friends"),
    path(
        "<int:pk>/explore/mutual/",
        ProfileExploreMutualFriendsView.as_view(),
        name="profile_explore_mutual_friends",
    ),
    path("<int:pk>/explore/posts/", ProfileExplorePostsView.as_view(), name="profile_explore_posts"),
    path("<int:pk>/explore/videos/", ProfileExploreVideosView.as_view(), name="profile_explore_videos"),
]

urlpatterns = [
    *core_urlpatterns,
    *settings_urlpatterns,
    *friendship_urlpatterns,
    *account_center_urlpatterns,
    *avatar_urlpatterns,
    *favorite_urlpatterns,
    *block_urlpatterns,
    *explore_urlpatterns,
]
