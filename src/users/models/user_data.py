from django.conf import settings
from django.db import models


class UserData(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_data",
    )

    data_1 = models.CharField(max_length=250)
    data_2 = models.CharField(max_length=250)
