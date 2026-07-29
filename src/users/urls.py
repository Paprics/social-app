# src/users/urls.py
from django.urls import path

from users.views import (
    ProfileView,
    SettingsAccountView,
    SettingsCommunicationView,
    SettingsLocalizationView,
    SettingsNotificationsView,
    SettingsPageView,
    SettingsPremiumFeaturesView,
    SettingsPrivacyView,
    SettingsProfileView,
    #
    GalleryView,
    SensitiveContentToggleView,
    PhotoUploadView,
    AlbumDetailView,
    AlbumSettingsView,
    PhotoDeleteView,
    #
    FriendRequestSendView,
    FriendRequestCancelView,
    FriendRequestAcceptView,
    FriendRequestDeclineView,
    FriendRemoveView,
    #
    AccountCenterView,
    #
    AvatarModalView,
    AvatarSetView,
    AvatarUploadView,
)

app_name = "users"

settings_urlpatterns = [
    path("<int:pk>/", ProfileView.as_view(), name="profile"),
    path("settings/", SettingsPageView.as_view(), name="settings"),
    path("settings/account/", SettingsAccountView.as_view(), name="account"),
    path("settings/profile/", SettingsProfileView.as_view(), name="settings_profile"),
    path("settings/privacy/", SettingsPrivacyView.as_view(), name="privacy"),
    path("settings/communication/", SettingsCommunicationView.as_view(), name="communication"),
    path("settings/notifications/", SettingsNotificationsView.as_view(), name="notifications"),
    path("settings/localization/", SettingsLocalizationView.as_view(), name="localization"),
    path("settings/premium-features/", SettingsPremiumFeaturesView.as_view(), name="premium_features"),
    path(
        "settings/preferences/sensitive-content/", SensitiveContentToggleView.as_view(), name="toggle_sensitive_content"
    ),
]

gallery_urlpatterns = [
    path("<int:pk>/gallery/", GalleryView.as_view(), name="gallery"),
    path("<int:pk>/gallery/<int:album_pk>/", AlbumDetailView.as_view(), name="album_detail"),
    path("<int:pk>/gallery/<int:album_pk>/settings/", AlbumSettingsView.as_view(), name="album_settings"),
    path("<int:pk>/gallery/<int:album_pk>/settings/save/", AlbumSettingsView.as_view(), name="album_settings_save"),
    path("photos/upload/", PhotoUploadView.as_view(), name="photo_upload"),
    path("photos/<int:photo_pk>/delete/", PhotoDeleteView.as_view(), name="photo_delete"),
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
]

avatar_urlpatterns = [
    path("profile/avatar/", AvatarModalView.as_view(), name="avatar_modal"),
    path("profile/avatar/set/", AvatarSetView.as_view(), name="avatar_set"),
    path("profile/avatar/upload/", AvatarUploadView.as_view(), name="avatar_upload"),
]

urlpatterns = [
    *settings_urlpatterns,
    *gallery_urlpatterns,
    *friendship_urlpatterns,
    *account_center_urlpatterns,
    *avatar_urlpatterns,
]
