from django.contrib import admin
from django.utils.html import format_html

from .models import Content, ContentLocale


class ContentLocaleInline(admin.StackedInline):
    """
    Inline-редактор локализованных версий контента.

    Позволяет редактировать все переводы непосредственно
    со страницы родительского объекта Content.
    """

    model = ContentLocale
    extra = 0
    min_num = 0

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "language",
                    "is_active",
                    "page_title",
                    "content_title",
                    "short_description",
                ),
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "plain_text",
                    "content",
                ),
            },
        ),
        (
            "SEO",
            {
                "fields": ("meta_description",),
            },
        ),
        (
            "Structured Data (JSON)",
            {
                "fields": ("json_data",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    """
    Администрирование основной сущности контента.

    Отображает общие свойства записи и позволяет управлять
    всеми локализованными версиями через Inline.
    """

    list_display = (
        "key",
        "content_type_badge",
        "slug",
        "is_active",
        "locales_preview",
        "updated_at",
    )

    list_filter = (
        "content_type",
        "is_active",
    )

    search_fields = (
        "key",
        "slug",
    )

    list_editable = ("is_active",)

    prepopulated_fields = {
        "slug": ("key",),
    }

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    date_hierarchy = "created_at"

    inlines = (ContentLocaleInline,)

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "key",
                    "content_type",
                    "slug",
                    "is_active",
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Type")
    def content_type_badge(self, obj):
        """
        Цветная метка типа контента.
        """

        colors = {
            Content.ContentType.SITE_PAGE: "#6c757d",
            Content.ContentType.ACADEMY: "#7c3aed",
            Content.ContentType.CONTENT: "#2563eb",
            Content.ContentType.JSON: "#ea580c",
        }

        color = colors.get(obj.content_type, "#6b7280")

        return format_html(
            (
                '<span style="'
                "background:{};"
                "color:white;"
                "padding:3px 8px;"
                "border-radius:6px;"
                "font-size:11px;"
                "font-weight:600;"
                '">{}</span>'
            ),
            color,
            obj.get_content_type_display(),
        )

    @admin.display(description="Locales")
    def locales_preview(self, obj):
        """
        Показывает доступные языковые версии.
        """

        languages = obj.locales.values_list("language", flat=True).order_by("language")

        if not languages:
            return format_html('<span style="color:#9ca3af;">—</span>')

        badges = []

        for language in languages:
            badges.append(
                format_html(
                    (
                        '<span style="'
                        "background:#16a34a;"
                        "color:white;"
                        "padding:2px 6px;"
                        "margin-right:3px;"
                        "border-radius:4px;"
                        "font-size:10px;"
                        '">{}</span>'
                    ),
                    language.upper(),
                )
            )

        return format_html(" ".join(str(b) for b in badges))

    def get_queryset(self, request):
        """
        Предварительно загружает локализации,
        чтобы избежать N+1 запросов.
        """
        return super().get_queryset(request).prefetch_related("locales")


@admin.register(ContentLocale)
class ContentLocaleAdmin(admin.ModelAdmin):
    """
    Администрирование локализованных версий контента.

    Используется для быстрого поиска и редактирования переводов
    без открытия родительской записи.
    """

    list_display = (
        "content_item",
        "language",
        "is_active",
        "content_title_preview",
        "seo_ready",
        "has_html",
        "has_json",
    )

    list_filter = (
        "language",
        "is_active",
        "content_item__content_type",
        "content_item__is_active",
    )

    search_fields = (
        "content_item__key",
        "content_item__slug",
        "page_title",
        "content_title",
        "short_description",
    )

    autocomplete_fields = ("content_item",)

    list_select_related = ("content_item",)

    list_editable = ("is_active",)

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "content_item",
                    "language",
                    "is_active",
                ),
            },
        ),
        (
            "SEO",
            {
                "fields": (
                    "page_title",
                    "meta_description",
                ),
            },
        ),
        (
            "Page Content",
            {
                "fields": (
                    "content_title",
                    "short_description",
                    "plain_text",
                    "content",
                ),
            },
        ),
        (
            "Structured Data (JSON)",
            {
                "fields": ("json_data",),
                "classes": ("collapse",),
                "description": (
                    "Optional structured data passed directly to the template context."
                ),
            },
        ),
    )

    @admin.display(description="Content title")
    def content_title_preview(self, obj):
        """
        Короткий предпросмотр H1.
        """

        if obj.content_title:
            if len(obj.content_title) <= 60:
                return obj.content_title

            return f"{obj.content_title[:60]}…"

        return format_html(
            '<span style="color:#9ca3af;font-style:italic;">— no title —</span>'
        )

    @admin.display(boolean=True, description="SEO")
    def seo_ready(self, obj):
        """
        Заполнены ли основные SEO-поля.
        """

        return bool(obj.page_title.strip() and obj.meta_description.strip())

    @admin.display(boolean=True, description="HTML")
    def has_html(self, obj):
        """
        Есть ли HTML-контент.
        """

        return bool(obj.content.strip())

    @admin.display(boolean=True, description="JSON")
    def has_json(self, obj):
        """
        Есть ли JSON.
        """

        return obj.json_data is not None

    def get_queryset(self, request):
        """
        Предварительно загружает родительский объект.
        """

        return super().get_queryset(request).select_related("content_item")
