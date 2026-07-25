from django.db import models


class Dialog(models.Model):
    user1 = models.ForeignKey(...)
    user2 = models.ForeignKey(...)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
