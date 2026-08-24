from django.conf import settings
from django.db import models


class UserData(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_data",
        null=True,
        blank=True,
    )
    username = models.CharField(max_length=250, blank=True, default="")
    data_1 = models.CharField(max_length=250, blank=True, default="")
    data_2 = models.CharField(max_length=250, blank=True, default="")

    def __str__(self):
        if self.username:
            return self.username

        if self.user:
            return self.user.get_username()

        return f"UserData #{self.pk}"
