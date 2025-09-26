"""Custom admin widgets with Jalali-friendly hints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from django.contrib.admin.widgets import AdminDateWidget, AdminSplitDateTime
from django.utils.dateparse import parse_date, parse_datetime, parse_time

from apps.common.jalali import format_jalali, format_jalali_date


class JalaliDateWidget(AdminDateWidget):
    """Render a date input with a Jalali equivalent hint."""

    template_name = "admin/widgets/jalali_date.html"

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None):
        context = super().get_context(name, value, attrs)
        context["jalali_display"] = format_jalali_date(self._coerce_to_date(value))
        return context

    def _coerce_to_date(self, value: Any) -> date | None:
        if value is None:
            return None

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            return parse_date(value)

        return None


class JalaliSplitDateTimeWidget(AdminSplitDateTime):
    """Render a datetime input that displays the Jalali conversion."""

    template_name = "admin/widgets/jalali_split_datetime.html"

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None):
        context = super().get_context(name, value, attrs)
        context["jalali_display"] = format_jalali(self._coerce_to_datetime(value))
        return context

    def _coerce_to_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            return parse_datetime(value)

        if isinstance(value, tuple | list) and len(value) == 2:
            date_part, time_part = value

            if isinstance(date_part, str):
                date_part = parse_date(date_part)

            if isinstance(time_part, str):
                time_part = parse_time(time_part)

            if isinstance(date_part, date) and time_part:
                return datetime.combine(date_part, time_part)

        return None
