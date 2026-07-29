# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType
# from django.db import models
# from django.contrib.auth import get_user_model
# from users.managers import
#
# User = get_user_model()
#
#
#
#
# class Favorite(models.Model):
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name="favorites",
#     )
#
#     content_type = models.ForeignKey(
#         ContentType,
#         on_delete=models.CASCADE,
#     )
#
#     object_id = models.PositiveBigIntegerField()
#
#     content_object = GenericForeignKey(
#         "content_type",
#         "object_id",
#     )
#
#     created_at = models.DateTimeField(
#         auto_now_add=True,
#     )
#
#     class Meta:
#         verbose_name = "Favorite"
#         verbose_name_plural = "Favorites"
#
#         ordering = ("-created_at",)
#
#         constraints = [
#             models.UniqueConstraint(
#                 fields=("user", "content_type", "object_id"),
#                 name="unique_favorite",
#             )
#         ]
#
#         indexes = [
#             models.Index(
#                 fields=("user", "content_type"),
#             ),
#         ]
#
#     def __str__(self):
#         return f"{self.user} → {self.content_object}"
#
#     objects = FavoriteManager()
