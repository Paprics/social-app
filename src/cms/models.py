from django.conf import settings
from django.db import models
from tinymce.models import HTMLField


class Content(models.Model):
    """
    Центральная модель контента.

    Хранит только общие данные, одинаковые для всех языковых версий:
    идентификатор, тип контента, slug и служебные признаки.

    Локализованный контент (SEO, HTML, текст, JSON) хранится
    в модели ContentLocale.
    """

    class ContentType(models.TextChoices):
        """
        Категория контента.

        Используется для разделения записей по назначению,
        а не по формату хранения данных.
        """

        SITE_PAGE = "site_page", "Site Page"
        ACADEMY = "academy", "Academy"
        CONTENT = "content", "Content"
        JSON = "json", "JSON Data"

    key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Key",
        help_text="Unique internal identifier used in code and queries.",
    )

    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.CONTENT,
        db_index=True,
        verbose_name="Content type",
        help_text="Determines which section of the site this record belongs to.",
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Slug",
        help_text="SEO-friendly URL slug. Usually generated from the key.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Is active",
        help_text="Enable or disable this content on the site.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created at",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated at",
    )

    class Meta:
        verbose_name = "Content"
        verbose_name_plural = "Content"
        ordering = ["key"]

    def save(self, *args, **kwargs):
        self.key = self.key.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.key


class ContentLocale(models.Model):
    """
    Локализованная версия контента.

    Каждая запись соответствует одному языку и содержит
    весь текстовый контент, SEO-данные и JSON,
    относящиеся к конкретной языковой версии.
    """

    content_item = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="locales",
        verbose_name="Relation content key",
        help_text="Parent content record.",
    )

    language = models.CharField(
        max_length=2,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )

    page_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Page title",
        help_text="HTML TAB title. Recommended: up to 60 characters.",
    )

    content_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Content title",
        help_text="H1 heading displayed on the page.",
    )

    short_description = models.TextField(
        blank=True,
        default="",
        verbose_name="Short description",
        help_text="Short summary used in cards and previews.",
    )

    plain_text = models.TextField(
        blank=True,
        default="",
        verbose_name="Plain text",
        help_text="Plain text without HTML formatting.",
    )

    content = HTMLField(
        blank=True,
        default="",
        verbose_name="Content",
        help_text="Main HTML content edited with TinyMCE.",
    )

    meta_description = models.TextField(
        blank=True,
        default="",
        verbose_name="Meta description",
        help_text="SEO meta description tag head. Recommended: up to 160 characters.",
    )

    json_data = models.JSONField(
        blank=True,
        null=True,
        default=None,
        verbose_name="JSON data",
        help_text="Structured JSON data for this language version.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Is active",
        help_text="Enable or disable this language version.",
    )

    class Meta:
        verbose_name = "Content locale"
        verbose_name_plural = "Content locales"
        ordering = ["language"]

        constraints = [
            models.UniqueConstraint(
                fields=("content_item", "language"),
                name="unique_content_locale",
            )
        ]

    def __str__(self):
        return f"{self.content_item.key} [{self.language.upper()}]"
