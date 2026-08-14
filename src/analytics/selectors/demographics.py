# src/analytics/selectors/demographics.py
"""Gender, age and looking-for aggregations."""

from collections import defaultdict
from datetime import date

from django.db.models import Count, Q
from django.utils import timezone

from analytics.dto.dashboard import AgeRow, GenderRow, Period
from users.models.profile import Profile

_AGE_BUCKETS = [
    ("18–20", 18, 20),
    ("21–24", 21, 24),
    ("25–29", 25, 29),
    ("30–34", 30, 34),
    ("35–39", 35, 39),
    ("40–49", 40, 49),
    ("50–59", 50, 59),
    ("60+",   60, 120),
]


def get_gender_rows() -> list[GenderRow]:
    """Распределение по gender (все активные профили)."""
    qs = (
        Profile.objects.filter(user__is_active=True)
        .exclude(gender="")
        .values("gender")
        .annotate(count=Count("id"))
    )
    total = sum(r["count"] for r in qs) or 1
    label_map = dict(Profile.Gender.choices)
    return [
        GenderRow(
            label=label_map.get(r["gender"], r["gender"]),
            count=r["count"],
            pct=round(r["count"] / total * 100, 1),
        )
        for r in sorted(qs, key=lambda x: -x["count"])
    ]


def get_age_rows() -> list[AgeRow]:
    """Распределение по возрастным группам."""
    today = timezone.localdate()
    rows = []
    qs_base = Profile.objects.filter(user__is_active=True, birth_date__isnull=False)
    total = qs_base.count() or 1

    for label, age_min, age_max in _AGE_BUCKETS:
        dob_max = date(today.year - age_min, today.month, today.day)
        dob_min = date(today.year - age_max - 1, today.month, today.day)
        count = qs_base.filter(birth_date__range=(dob_min, dob_max)).count()
        rows.append(AgeRow(label=label, count=count, pct=round(count / total * 100, 1)))

    return rows


def get_looking_for_matrix() -> dict:
    """
    Матрица gender × looking_for.
    Возвращает dict {from_gender: {to_gender: pct}}.
    """
    label_map = dict(Profile.Gender.choices)
    gender_values = [g[0] for g in Profile.Gender.choices]
    matrix: dict[str, dict[str, float]] = {}

    for gender in gender_values:
        total = Profile.objects.filter(
            user__is_active=True, gender=gender
        ).exclude(looking_for=[]).count() or 1

        row: dict[str, float] = {}
        for target in gender_values:
            count = Profile.objects.filter(
                user__is_active=True,
                gender=gender,
                looking_for__contains=[target],
            ).count()
            row[label_map[target]] = round(count / total * 100, 1)

        matrix[label_map[gender]] = row

    return matrix
