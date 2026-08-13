"""Access rules for image attachments in posts."""


class PostMediaAccessService:
    """
    Decide whether a user may use image attachments in posts.

    Image attachments are temporarily limited to staff users.
    Keeping this rule in one place makes it easy to replace the staff gate
    later with premium access or another permission without changing services,
    views, or templates.
    """

    @staticmethod
    def can_attach_images(*, user, post=None) -> bool:
        """Return whether the user may manage image attachments."""

        if not user or not user.is_authenticated:
            return False

        if not user.is_staff:
            return False

        # Media of an existing post may only be managed by its author.
        if post is not None and post.author_id != user.id:
            return False

        return True
