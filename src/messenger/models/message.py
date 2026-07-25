from django.db import models


class Message(models.Model):
    dialog = models.ForeignKey()

    sender = models.ForeignKey()

    text = models.TextField()

    created_at = ...
