# src/analytics/templatetags/analytics_tags.py
"""Custom template filters and tags for analytics dashboard."""

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def keys(d: dict):
    """Вернуть ключи словаря (для итерации в шаблоне)."""
    return d.keys() if isinstance(d, dict) else []


@register.filter
def items(d: dict):
    """Вернуть items словаря."""
    return d.items() if isinstance(d, dict) else []


@register.filter
def intcomma(value):
    """Форматировать число с разделителем тысяч."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


@register.filter
def filesizeformat(bytes_val):
    """Читаемый размер файла."""
    try:
        b = int(bytes_val)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
