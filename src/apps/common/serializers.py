"""Reusable serializer components for the ExamBoard project."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

from rest_framework import serializers

from . import jalali


class JalaliDateTimeField(serializers.DateTimeField):
    """Serialize datetimes with a Jalali companion representation."""

    default_error_messages = {
        "invalid": "ساختار تاریخ و زمان معتبر نیست.",
        "null": "ارزش این فیلد نمی‌تواند خالی باشد.",
    }

    def to_representation(self, value: Any) -> Any:  # noqa: ANN401
        if value is None:
            return None

        datetime_value = value
        if not isinstance(datetime_value, datetime):
            datetime_value = self.to_internal_value(value)
        else:
            datetime_value = jalali.ensure_aware(datetime_value)
        utc_value = datetime_value.astimezone(UTC)
        iso_value = utc_value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return {
            "iso": iso_value,
            "jalali": jalali.format_jalali(datetime_value),
        }


class JalaliDateField(serializers.DateField):
    """Serialize dates alongside their Jalali representation."""

    default_error_messages = {
        "invalid": "ساختار تاریخ معتبر نیست.",
        "null": "ارزش این فیلد نمی‌تواند خالی باشد.",
    }

    def to_representation(self, value: Any) -> Any:  # noqa: ANN401
        if value is None:
            return None

        date_value: date
        if isinstance(value, date) and not isinstance(value, datetime):
            date_value = value
        else:
            parsed = super().to_representation(value)
            if isinstance(parsed, str):
                date_value = super().to_internal_value(parsed)
            elif isinstance(parsed, date):
                date_value = parsed
            else:
                raise TypeError("Expected a string or date representation")

        local_dt = datetime.combine(date_value, time.min)
        aware_local = jalali.ensure_aware(local_dt)
        jalali_value = jalali.format_jalali(aware_local)

        return {
            "iso": date_value.isoformat(),
            "jalali": jalali_value,
        }
