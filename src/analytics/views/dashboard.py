# src/analytics/views/dashboard.py
"""Admin analytics dashboard view — staff only."""

import json
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from analytics.services.dashboard import build_dashboard
from analytics.services.periods import build_period

_VALID_PERIODS = {
    "24h",
    "7d",
    "30d",
    "90d",
    "year",
    "all",
    "custom",
}


@method_decorator(staff_member_required, name="dispatch")
class AnalyticsDashboardView(TemplateView):
    """Render the staff-only analytics dashboard."""

    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        period_label = self._get_period_label()
        period = self._build_period(period_label)
        data = build_dashboard(period)

        ctx["data"] = data
        ctx["period_label"] = period_label

        # Time-series charts.
        ctx["chart_registrations"] = self._chart_json(
            data.registrations_chart,
        )
        ctx["chart_active"] = self._chart_json(
            data.active_users_chart,
        )
        ctx["chart_hours"] = self._chart_json(
            data.activity_by_hour,
        )

        # Demographic charts.
        ctx["gender_labels"] = self._json_dumps(
            [row.label for row in data.gender_rows],
        )
        ctx["gender_values"] = self._json_dumps(
            [row.count for row in data.gender_rows],
        )

        ctx["age_labels"] = self._json_dumps(
            [row.label for row in data.age_rows],
        )
        ctx["age_values"] = self._json_dumps(
            [row.count for row in data.age_rows],
        )

        # Gender × looking-for matrix.
        ctx["looking_for_columns"] = self._matrix_columns(
            data.looking_for_matrix,
        )

        return ctx

    def _get_period_label(self) -> str:
        """Return a validated period name from the query string."""

        label = self.request.GET.get(
            "period",
            "30d",
        )

        if label in _VALID_PERIODS:
            return label

        return "30d"

    def _build_period(self, label):
        """Build the selected analytics period."""

        if label == "custom":
            try:
                date_from = datetime.fromisoformat(
                    self.request.GET.get(
                        "from",
                        "",
                    )
                )
                date_to = datetime.fromisoformat(
                    self.request.GET.get(
                        "to",
                        "",
                    )
                )

                return build_period(
                    "custom",
                    date_from,
                    date_to,
                )

            except (ValueError, TypeError):
                pass

        return build_period(label)

    @classmethod
    def _chart_json(cls, points) -> str:
        """Serialize chart points for frontend JavaScript."""

        return cls._json_dumps(
            {
                "labels": [point.label for point in points],
                "values": [point.value for point in points],
            }
        )

    @staticmethod
    def _matrix_columns(matrix) -> list:
        """Return column labels from the first row of a matrix."""

        if not matrix:
            return []

        first_row = next(
            iter(matrix.values()),
            {},
        )

        return list(first_row.keys())

    @staticmethod
    def _json_dumps(value) -> str:
        """Serialize dashboard data including Django-specific values."""

        return json.dumps(
            value,
            cls=DjangoJSONEncoder,
            ensure_ascii=False,
        )
