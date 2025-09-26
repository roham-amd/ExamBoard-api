from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from apps.common import jalali


@pytest.mark.parametrize(
    "iso_value",
    [
        datetime(2025, 7, 1, 8, 0, tzinfo=ZoneInfo("UTC")),
        datetime(2024, 3, 20, 3, 30, tzinfo=ZoneInfo("UTC")),
    ],
)
def test_format_and_parse_round_trip(iso_value: datetime) -> None:
    jalali_string = jalali.format_jalali(iso_value)
    parsed = jalali.parse_jalali(jalali_string)
    assert parsed.astimezone(ZoneInfo("UTC")) == iso_value


def test_format_jalali_matches_expected_output() -> None:
    dt = datetime(2025, 7, 1, 8, 0, tzinfo=ZoneInfo("UTC"))
    assert jalali.format_jalali(dt) == "1404-04-10 11:30"


def test_format_jalali_date_matches_expected_output() -> None:
    gregorian = date(2024, 3, 20)
    assert jalali.format_jalali_date(gregorian) == "1403-01-01"
