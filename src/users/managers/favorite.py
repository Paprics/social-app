from django.contrib.contenttypes.models import ContentType
from django.db import models


class FavoriteQuerySet(models.QuerySet):
    def for_user(self, user):
        """Избранное пользователя."""
        return self.filter(user=user)

    def for_model(self, model):
        """Фильтр по типу модели."""
        content_type = ContentType.objects.get_for_model(model)

        return self.filter(content_type=content_type)

    def is_favorite(self, user, obj):
        """Проверяет, находится ли объект в избранном пользователя."""
        content_type = ContentType.objects.get_for_model(
            obj,
            for_concrete_model=False,
        )

        return self.filter(
            user=user,
            content_type=content_type,
            object_id=obj.pk,
        ).exists()


class FavoriteManager(models.Manager.from_queryset(FavoriteQuerySet)):
    """Менеджер модели Favorite."""

    pass
