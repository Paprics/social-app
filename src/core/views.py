# core/views.py
import logging

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import TemplateView
from geo.models import Country

from cms.models import ContentLocale

logger = logging.getLogger(__name__)

# Поддерживаемые языки сайта
SUPPORTED_LANGUAGES = {"en", "ru", "uk"}
DEFAULT_LANGUAGE = "en"


def _resolve_language(request) -> str:
    """
    Определяет язык контента для анонимного пользователя.

    Приоритет:
    1. GET-параметр ?lang=
    2. Язык из Django i18n (выбранный переключателем)
    3. Accept-Language из браузера
    4. Дефолт — English

    Если язык не поддерживается — возвращает DEFAULT_LANGUAGE.
    """
    # 1. Явный GET-параметр (для отладки и прямых ссылок)
    lang = request.GET.get("lang", "").strip().lower()[:5]
    if lang in SUPPORTED_LANGUAGES:
        logger.debug("Language from GET param: %s", lang)
        return lang

    # 2. Язык, активированный Django i18n (переключатель в хедере)
    from django.utils import translation

    active_lang = translation.get_language()
    if active_lang:
        code = active_lang.split("-")[0].lower()
        if code in SUPPORTED_LANGUAGES:
            logger.debug("Language from Django i18n: %s", code)
            return code

    # 3. Accept-Language из браузера
    accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    for part in accept.split(","):
        code = part.strip().split(";")[0].split("-")[0].lower()
        if code in SUPPORTED_LANGUAGES:
            logger.debug("Language from Accept-Language header: %s", code)
            return code

    logger.debug("Language fallback to default: %s", DEFAULT_LANGUAGE)
    return DEFAULT_LANGUAGE


class IndexView(TemplateView):
    template_name = "index.html"

    def dispatch(self, request, *args, **kwargs):
        # Авторизованного пользователя сразу на его профиль
        if request.user.is_authenticated:
            return redirect("users:profile", pk=request.user.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = _resolve_language(self.request)

        content = (
            ContentLocale.objects.select_related("content_item")
            .filter(
                content_item__key="index",
                language=lang,
                is_active=True,
                content_item__is_active=True,
            )
            .first()
        )

        # Если запрошенный язык не найден — пробуем английский
        if content is None and lang != DEFAULT_LANGUAGE:
            logger.warning(
                "Content not found for lang=%s, falling back to %s",
                lang,
                DEFAULT_LANGUAGE,
            )
            content = (
                ContentLocale.objects.select_related("content_item")
                .filter(
                    content_item__key="index",
                    language=DEFAULT_LANGUAGE,
                    is_active=True,
                    content_item__is_active=True,
                )
                .first()
            )

        if content is None:
            logger.error("Index content not found in DB for any supported language.")
            # raise Http404("Index content is not available.")

        context["content"] = content

        context["countries"] = Country.objects.filter(
            code2__in=settings.GEO_ALLOWED_COUNTRIES
        )

        return context
