# users/urls.py
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
    PhotoAlbumListView,
    PhotoAlbumDetailView,
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
]

gallery_urlpatterns = [
    # Фото
    path("<int:pk>/photos/", PhotoAlbumListView.as_view(), name="photo_albums"),
    path("<int:pk>/photos/<int:album_pk>/", PhotoAlbumDetailView.as_view(), name="photo_album"),
    # Видео (Later)
    # path("<int:pk>/videos/", VideoAlbumListView.as_view(), name="video_albums"),
    # path("<int:pk>/videos/<int:album_pk>/", VideoAlbumDetailView.as_view(), name="video_album"),
]


urlpatterns = [
    *settings_urlpatterns,
    *gallery_urlpatterns,
]
