# src/analytics/dto/dashboard.py
"""Frozen dataclasses passed from services to views."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Period:
    """Временной период с границами и гранулярностью."""
    label: str          # "30d", "7d", "24h", "year", "all"
    start: datetime
    end: datetime
    prev_start: datetime
    prev_end: datetime
    granularity: str    # "hour", "day", "week", "month"


@dataclass(frozen=True)
class StatCard:
    """Одна метрика в overview-блоке."""
    label: str
    value: int | float
    prev_value: int | float
    unit: str = ""      # "", "%", "MB" и т.п.
    fmt: str = "int"    # "int" | "float" | "size"

    @property
    def delta(self) -> float:
        """Изменение в % относительно предыдущего периода."""
        if not self.prev_value:
            return 0.0
        return round((self.value - self.prev_value) / self.prev_value * 100, 1)

    @property
    def delta_positive(self) -> bool:
        return self.delta >= 0


@dataclass(frozen=True)
class ChartPoint:
    label: str
    value: int | float


@dataclass(frozen=True)
class GenderRow:
    label: str
    count: int
    pct: float


@dataclass(frozen=True)
class AgeRow:
    label: str
    count: int
    pct: float


@dataclass(frozen=True)
class GeoRow:
    name: str
    count: int
    pct: float


@dataclass(frozen=True)
class FunnelStep:
    label: str
    count: int
    pct: float          # относительно первого шага воронки


@dataclass(frozen=True)
class HealthRow:
    label: str
    count: int
    pct: float


@dataclass(frozen=True)
class StorageStats:
    total_bytes: int
    media_bytes: int
    avatars_bytes: int
    files_count: int

    @property
    def total_mb(self) -> float:
        return round(self.total_bytes / 1024 / 1024, 1)

    @property
    def media_mb(self) -> float:
        return round(self.media_bytes / 1024 / 1024, 1)

    @property
    def avatars_mb(self) -> float:
        return round(self.avatars_bytes / 1024 / 1024, 1)


@dataclass
class DashboardData:
    """Полный payload для шаблона dashboard."""
    period: Period

    # Overview
    overview: list[StatCard] = field(default_factory=list)

    # Growth charts
    registrations_chart: list[ChartPoint] = field(default_factory=list)
    active_users_chart: list[ChartPoint] = field(default_factory=list)

    # Demographics
    gender_rows: list[GenderRow] = field(default_factory=list)
    age_rows: list[AgeRow] = field(default_factory=list)
    looking_for_matrix: dict = field(default_factory=dict)

    # Geography
    top_countries: list[GeoRow] = field(default_factory=list)
    top_regions: list[GeoRow] = field(default_factory=list)
    top_cities: list[GeoRow] = field(default_factory=list)

    # Activity
    activity_by_hour: list[ChartPoint] = field(default_factory=list)
    online_buckets: list[StatCard] = field(default_factory=list)

    # Media
    media_stats: list[StatCard] = field(default_factory=list)
    storage: StorageStats | None = None

    # Social
    social_stats: list[StatCard] = field(default_factory=list)
    messaging_stats: list[StatCard] = field(default_factory=list)

    # Content
    content_stats: list[StatCard] = field(default_factory=list)

    # Funnel
    funnel: list[FunnelStep] = field(default_factory=list)

    # Health
    health_rows: list[HealthRow] = field(default_factory=list)
