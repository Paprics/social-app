"""
Template tag for reusable image rendering.

Provides thumbnail generation through easy-thumbnails and prepares
image rendering options such as fallback images, media blur, reveal
controls, alternative text, custom CSS classes, and image shape.

Related:
- Template: core/components/media/thumbnail_image.html
- CSS: static/css/components/image_blur.css
- JavaScript: static/js/components/image_blur.js
"""

from django import template
from django.templatetags.static import static
from easy_thumbnails.files import get_thumbnailer

register = template.Library()


@register.inclusion_tag(
    "core/components/media/thumbnail_image.html",
    takes_context=True,
)
def render_image(
    context,
    image,
    *,
    variant="avatar_sm",
    alt="",
    css_class="",
    reveal=False,
    shape=None,
):
    """
    Render an image using a configured easy-thumbnails alias.

    If no source image is provided, the default avatar is used.

    The current user's ``blur_media`` preference determines whether
    the resulting image should be blurred. ``reveal`` controls whether
    a blurred image can be revealed and hidden again by the user.

    ``shape`` optionally controls the shape of the entire media
    component. Currently ``circle`` is supported. If omitted, the
    existing/default component geometry is preserved.
    """
    request = context.get("request")

    should_blur = bool(request and request.user.is_authenticated and request.user.settings.blur_media)

    if image:
        thumbnail = get_thumbnailer(image)[variant]
        image_url = thumbnail.url
    else:
        image_url = static("images/placeholders/default-avatar.svg")

    return {
        "image_url": image_url,
        "alt": alt,
        "css_class": css_class,
        "should_blur": should_blur,
        "show_reveal": should_blur and reveal,
        "shape": shape,
    }
