from django.contrib.contenttypes.models import ContentType

from users.models.favorite import Favorite


class FavoriteService:
    @classmethod
    def _get_content_type(cls, obj):
        """Возвращает ContentType для объекта."""

        return ContentType.objects.get_for_model(
            obj,
            for_concrete_model=False,
        )

    @classmethod
    def add(cls, user, obj):
        """Добавляет объект в избранное пользователя."""

        favorite, _ = Favorite.objects.get_or_create(
            user=user,
            content_type=cls._get_content_type(obj),
            object_id=obj.pk,
        )

        return favorite

    @classmethod
    def remove(cls, user, obj):
        """Удаляет объект из избранного пользователя."""

        Favorite.objects.filter(
            user=user,
            content_type=cls._get_content_type(obj),
            object_id=obj.pk,
        ).delete()

    @classmethod
    def toggle(cls, user, obj):
        """Переключает состояние объекта в избранном.

        Returns:
            bool: True, если объект был добавлен в избранное,
                  False, если был удален.
        """

        if cls.is_favorite(user, obj):
            cls.remove(user, obj)
            return False

        cls.add(user, obj)
        return True

    @classmethod
    def is_favorite(cls, user, obj):
        """Проверяет, находится ли объект в избранном."""

        return Favorite.objects.is_favorite(user, obj)
