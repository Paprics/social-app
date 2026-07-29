# profile.py
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    # TODO Переопределить удаление!!!

    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")
        COUPLE = "couple", _("Couple")
        NON_BINARY = "non_binary", _("Non-binary")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text=_("The user account associated with this profile."),
    )

    is_verified = models.BooleanField(
        default=False,
        help_text=_("Indicates whether the user's identity has been verified."),
    )

    is_deleted = models.BooleanField(
        default=False,
        help_text=_("Soft-delete flag. Deleted profiles remain in the database."),
    )

    is_banned = models.BooleanField(
        default=False,
        help_text=_("Indicates whether the profile has been banned by moderators."),
    )

    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text=_("Unique Telegram user ID linked to this account."),
    )

    telegram_data = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Cached Telegram profile data received during authentication."),
    )

    avatar_photo = models.ForeignKey(
        "users.Photo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Avatar"),
        help_text=_("Selected profile avatar."),
    )

    bio = models.TextField(
        max_length=500,
        blank=True,
        validators=[MaxLengthValidator(500)],
        help_text=_("Short personal description displayed on the profile."),
    )

    status = models.TextField(
        max_length=150,
        blank=True,
        validators=[MaxLengthValidator(150)],
        help_text=_("A short status displayed on your profile (up to 150 characters)."),
    )

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
        help_text=_("User's gender or profile type."),
    )

    looking_for = ArrayField(
        base_field=models.CharField(
            max_length=20,
            choices=Gender.choices,
        ),
        default=list,
        blank=True,
        help_text=_("Profiles the user is interested in meeting."),
    )

    open_to_gifts = models.BooleanField(
        default=False, help_text=_("Open to dating where gifts or financial support may be part of the relationship.")
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("User's date of birth."),
    )

    # =========== GEO =============
    country = models.ForeignKey(
        "geo.Country",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Country",
    )
    region = models.ForeignKey(
        "geo.Region",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Region",
    )
    city = models.ForeignKey(
        "geo.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="City",
    )

    # TODO:
    # Later this field will become a relation to PremiumPurchase.
    # For now it stores the Premium expiration date.
    premium = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Premium subscription expiration date and time."),
    )

    last_seen = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("Last recorded online activity."),
    )

    profile_views = models.PositiveIntegerField(
        default=0,
        help_text=_("Total number of profile views."),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Date and time when the profile was created."),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Date and time when the profile was last updated."),
    )

    @property
    def is_premium(self) -> bool:
        return self.premium is not None and self.premium > timezone.now()

    @property
    def age(self) -> int:
        today = timezone.localdate()

        years = today.year - self.birth_date.year

        if (today.month, today.day) < (
            self.birth_date.month,
            self.birth_date.day,
        ):
            years -= 1

        return years

    def __str__(self) -> str:
        return f"{self.user.username} [{self.user.pk}]"

    class Meta:
        indexes = [
            GinIndex(fields=["looking_for"]),
        ]
