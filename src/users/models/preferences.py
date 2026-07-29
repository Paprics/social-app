# preferences.py
from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    """
    Stores user preferences, privacy settings, communication permissions,
    notifications, and localization options.
    """

    class ProfileVisibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FRIENDS = "friends", "Friends only"
        PRIVATE = "private", "Private"

    class PermissionLevel(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        FRIENDS = "friends", "Friends only"
        NOBODY = "nobody", "Nobody"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings",
        help_text="The user these settings belong to.",
    )

    # -------- Privacy --------

    blur_sensitive = models.BooleanField(
        default=False,
        help_text="Blur images and media marked as sensitive until you choose to reveal them.",
    )

    profile_visibility = models.CharField(
        max_length=16,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        help_text="Controls who can view the user's profile.",
    )

    show_online_status = models.BooleanField(
        default=True,
        help_text="Display online status to other users.",
    )

    friends_visibility = models.CharField(
        max_length=16,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        help_text="Controls who can view the friends list.",
    )

    photo_albums_visibility = models.CharField(
        max_length=16,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        help_text="Controls who can view photo albums.",
    )

    wall_enabled = models.BooleanField(
        default=True,
        help_text="Enable the wall on the user's profile.",
    )

    # -------- Communication --------

    message_permission = models.CharField(
        max_length=16,
        choices=PermissionLevel.choices,
        default=PermissionLevel.EVERYONE,
        help_text="Controls who can send private messages.",
    )

    comment_permission = models.CharField(
        max_length=16,
        choices=PermissionLevel.choices,
        default=PermissionLevel.EVERYONE,
        help_text="Controls who can leave comments.",
    )

    wall_post_permission = models.CharField(
        max_length=16,
        choices=PermissionLevel.choices,
        default=PermissionLevel.FRIENDS,
        help_text="Controls who can publish posts on the user's wall.",
    )

    # -------- Notifications --------
    #
    # notify_messages = models.BooleanField(
    #     default=True,
    #     help_text="Receive notifications about new messages.",
    # )
    #
    # notify_friend_requests = models.BooleanField(
    #     default=True,
    #     help_text="Receive notifications about friend requests.",
    # )

    # -------- Localization --------

    language = models.CharField(
        max_length=2,
        choices=settings.LANGUAGES,
        default="en",
        help_text="Preferred interface language.",
    )

    # -------- Other --------

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the settings were created.",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the settings were last updated.",
    )

    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self):
        return f"Settings ({self.user})"


class UserPremiumFeatures(models.Model):
    """
    Stores optional premium-only features and preferences available
    to users with an active Premium subscription.

    This model is reserved for future feature expansion.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="premium_features",
        help_text="The user who owns these premium features.",
    )

    # -------- Privacy --------

    incognito_mode = models.BooleanField(
        default=False,
        help_text="Browse profiles without appearing in visitors lists.",
    )

    anonymous_profile_views = models.BooleanField(
        default=False,
        help_text="Hide profile visit activity from other users.",
    )

    hide_online_status_from_everyone = models.BooleanField(
        default=False,
        help_text="Completely hide online status from all users.",
    )

    # -------- Random Chat --------

    random_chat_gender_filter = models.BooleanField(
        default=False,
        help_text="Enable gender filtering in random chat.",
    )

    random_chat_country_filter = models.BooleanField(
        default=False,
        help_text="Enable country filtering in random chat.",
    )

    random_chat_language_filter = models.BooleanField(
        default=False,
        help_text="Enable language filtering in random chat.",
    )

    random_chat_age_filter = models.BooleanField(
        default=False,
        help_text="Enable age filtering in random chat.",
    )

    priority_matching = models.BooleanField(
        default=False,
        help_text="Prioritize matching with other users.",
    )

    # -------- Search --------

    advanced_search = models.BooleanField(
        default=False,
        help_text="Enable advanced search filters.",
    )

    unlimited_search_radius = models.BooleanField(
        default=False,
        help_text="Remove search distance limitations.",
    )

    # -------- Video --------

    hd_video = models.BooleanField(
        default=False,
        help_text="Enable high-definition video calls.",
    )

    # -------- Messaging --------

    unsend_messages = models.BooleanField(
        default=False,
        help_text="Allow deleting messages after sending.",
    )

    scheduled_messages = models.BooleanField(
        default=False,
        help_text="Allow scheduling messages for future delivery.",
    )

    extended_message_editing = models.BooleanField(
        default=False,
        help_text="Extend the time limit for editing messages.",
    )

    # -------- Profile --------

    custom_profile_theme = models.BooleanField(
        default=False,
        help_text="Allow custom profile themes.",
    )

    animated_profile_badge = models.BooleanField(
        default=False,
        help_text="Display an animated premium profile badge.",
    )

    profile_accent_color = models.BooleanField(
        default=False,
        help_text="Allow custom profile accent colors.",
    )

    # -------- Analytics --------

    profile_statistics = models.BooleanField(
        default=False,
        help_text="Access detailed profile statistics.",
    )

    profile_visitors = models.BooleanField(
        default=False,
        help_text="See who visited your profile.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the premium feature set was created.",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the premium feature set was last updated.",
    )

    # premium_badge_visible

    class Meta:
        verbose_name = "User Premium Features"
        verbose_name_plural = "User Premium Features"

    def __str__(self):
        return f"Premium Features ({self.user})"
