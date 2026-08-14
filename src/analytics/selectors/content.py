# src/analytics/selectors/content.py
"""Posts, comments and profile visits statistics."""

from django.db.models import Count

from analytics.dto.dashboard import Period, StatCard
from posts.models.comment import Comment
from posts.models.post import Post
from users.models.visit import ProfileVisit


def get_content_stats(period: Period) -> list[StatCard]:
    """Посты, комментарии и посещения профилей."""
    total_posts = Post.objects.count()
    new_posts = Post.objects.filter(created_at__range=(period.start, period.end)).count()
    prev_posts = Post.objects.filter(
        created_at__range=(period.prev_start, period.prev_end)
    ).count()

    total_comments = Comment.objects.count()
    new_comments = Comment.objects.filter(
        created_at__range=(period.start, period.end)
    ).count()
    prev_comments = Comment.objects.filter(
        created_at__range=(period.prev_start, period.prev_end)
    ).count()

    total_visits = ProfileVisit.objects.count()
    new_visits = ProfileVisit.objects.filter(
        visited_at__range=(period.start, period.end)
    ).count()
    prev_visits = ProfileVisit.objects.filter(
        visited_at__range=(period.prev_start, period.prev_end)
    ).count()

    return [
        StatCard("Total posts", total_posts, total_posts - new_posts),
        StatCard("New posts", new_posts, prev_posts),
        StatCard("Total comments", total_comments, total_comments - new_comments),
        StatCard("New comments", new_comments, prev_comments),
        StatCard("Profile visits", new_visits, prev_visits),
        StatCard("Total visits recorded", total_visits, 0),
    ]
