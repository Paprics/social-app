# content/views.py
from content.models import Content
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = "pages/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lang = self.request.LANGUAGE_CODE

        content = get_object_or_404(
            Content,
            key="about",
            is_active=True,
        )

        translation = content.locales.filter(
            language=lang,
            is_active=True,
        ).first()

        if translation is None:
            translation = content.locales.filter(
                language="en",
                is_active=True,
            ).first()

        if translation is None:
            raise Http404("Content translation not found.")

        context["translation"] = translation
        return context


def robots_txt(request):
    content = """
User-agent: *
Disallow: /admin/
Disallow: /i18n/

Sitemap: https://peekdrop.xyz/sitemap.xml
""".strip()

    return HttpResponse(
        content,
        content_type="text/plain",
    )
