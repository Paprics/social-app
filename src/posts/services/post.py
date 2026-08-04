from posts.models import Post


class PostService:
    """Сервис для управления записями на стене."""

    @staticmethod
    def create(*, owner, author, content):
        return Post.objects.create(
            owner=owner,
            author=author,
            content=content,
        )

    @staticmethod
    def update(*, post, content):
        post.content = content
        post.save(update_fields=["content"])

        return post

    @staticmethod
    def delete_post(post: Post) -> None:
        post.delete()
