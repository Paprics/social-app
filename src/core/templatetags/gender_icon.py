from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


GENDER_ICONS = {
    "male": {
        "icon": "icons/gender/male.svg",
        "color": "#3B82F6",
    },
    "female": {
        "icon": "icons/gender/female.svg",
        "color": "#EC4899",
    },
    "couple": {
        "icon": "icons/gender/couple.svg",
        "color": "#A855F7",
    },
    "non_binary": {
        "icon": "icons/gender/non_binary.svg",
        "color": "#14B8A6",
    },
}


@lru_cache(maxsize=len(GENDER_ICONS))
def _load_svg(icon_path: str) -> str:
    """
    Load an SVG file from static files.

    The result is cached because gender icons are immutable
    application assets and may be rendered many times per page.
    """
    path = settings.BASE_DIR / "static" / icon_path
    return Path(path).read_text(encoding="utf-8")


@register.simple_tag
def gender_icon(gender, size=16):
    """
    Render an inline SVG icon for the given gender.

    Usage:
        {% gender_icon profile.gender %}
        {% gender_icon profile.gender size=24 %}
    """
    if not gender:
        return ""

    icon_data = GENDER_ICONS.get(str(gender))

    if not icon_data:
        return ""

    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 16

    if size <= 0:
        size = 16

    try:
        svg = _load_svg(icon_data["icon"])
    except OSError:
        return ""

    svg = svg.replace(
        "<svg ",
        (
            f'<svg width="{size}" '
            f'height="{size}" '
            f'style="color:{icon_data["color"]};" '
            f'class="inline-block shrink-0" '
            f'aria-hidden="true" '
        ),
        1,
    )

    return mark_safe(svg)
