# src/search/selectors.py

from django.db.models import Q
from django.utils import timezone

from users.models.profile import Profile


def _years_ago(value, years):
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(
            year=value.year - years,
            month=2,
            day=28,
        )


def get_users_for_search(*, request_user, filters):
    query = Q(
        is_deleted=False,
        is_banned=False,
        user__is_active=True,
    )

    query &= ~Q(user=request_user)

    gender = filters.get("gender")
    if gender:
        query &= Q(gender=gender)

    country = filters.get("country")
    if country:
        query &= Q(country=country)

    region = filters.get("region")
    if region:
        query &= Q(region=region)

    city = filters.get("city")
    if city:
        query &= Q(city=city)

    today = timezone.localdate()

    age_from = filters.get("age_from")
    if age_from is not None:
        query &= Q(
            birth_date__lte=_years_ago(today, age_from),
        )

    age_to = filters.get("age_to")
    if age_to is not None:
        query &= Q(
            birth_date__gt=_years_ago(today, age_to + 1),
        )

    return (
        Profile.objects.select_related(
            "user",
            "avatar_photo",
            "country",
            "region",
            "city",
        )
        .filter(query)
        .order_by("-last_seen", "-created_at")
    )
