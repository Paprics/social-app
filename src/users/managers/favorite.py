# from django.contrib.contenttypes.models import ContentType
# from django.db import models
#
#
# class FavoriteQuerySet(models.QuerySet):
#
#     def for_user(self, user):
#         return self.filter(user=user)
#
#     def by_model(self, model):
#         return self.filter(content_type=ContentType.objects.get_for_model(model))
#
#     def profiles(self):
#         from accounts.models import UserProfile
#
#         return self.by_model(UserProfile)
#
#     def photos(self):
#         from media.models import Photo
#
#         return self.by_model(Photo)
