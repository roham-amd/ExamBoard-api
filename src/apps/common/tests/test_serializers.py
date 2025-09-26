from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.common.serializers import JalaliDateTimeField


class SampleSerializer(serializers.Serializer[dict[str, Any]]):
    scheduled_at = JalaliDateTimeField()


def test_jalali_field_representation() -> None:
    serializer = SampleSerializer()
    value = datetime(2025, 7, 1, 8, 0, tzinfo=ZoneInfo("UTC"))
    result = serializer.fields["scheduled_at"].to_representation(value)
    assert result == {
        "iso": "2025-07-01T08:00:00Z",
        "jalali": "1404-04-10 11:30",
    }


def test_jalali_field_accepts_iso_input() -> None:
    serializer = SampleSerializer(data={"scheduled_at": "2025-07-01T08:00:00Z"})
    assert serializer.is_valid(), serializer.errors
    expected = datetime(2025, 7, 1, 8, 0, tzinfo=ZoneInfo("UTC"))
    assert serializer.validated_data["scheduled_at"] == expected


def test_jalali_field_invalid_input_message() -> None:
    serializer = SampleSerializer(data={"scheduled_at": "not-a-date"})
    assert not serializer.is_valid()
    error = serializer.errors["scheduled_at"][0]
    assert "ساختار تاریخ" in error
    with pytest.raises(ValidationError):
        serializer.fields["scheduled_at"].run_validation("not-a-date")
