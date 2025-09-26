"""Reusable serializer components for the ExamBoard project."""

from __future__ import annotations

from datetime import UTC, datetime
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
