# core/views.py

from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import TemplateView

from cms.models import ContentLocale
from geo.models import Country


class IndexView(TemplateView):
    """Главная страница сайта."""

    template_name = "core/index.html"

    def dispatch(self, request, *args, **kwargs):
        """Перенаправляет авторизованного пользователя в его профиль."""
        if request.user.is_authenticated:
            return redirect("users:profile", pk=request.user.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Формирует контекст главной страницы."""
        context = super().get_context_data(**kwargs)

        language = self.request.LANGUAGE_CODE

        content = self._get_content(language)

        # Используем язык по умолчанию, если перевод отсутствует.
        if content is None and language != settings.LANGUAGE_CODE:
            content = self._get_content(settings.LANGUAGE_CODE)

        context["content"] = content
        context["countries"] = Country.objects.filter(
            code2__in=settings.GEO_ALLOWED_COUNTRIES,
        )

        return context

    @staticmethod
    def _get_content(language):
        """Возвращает локализованный контент главной страницы."""
        return (
            ContentLocale.objects.select_related("content_item")
            .filter(
                content_item__key="index",
                language=language,
                is_active=True,
                content_item__is_active=True,
            )
            .first()
        )
