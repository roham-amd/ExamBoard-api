"""Utility helpers for working with Jalali dates."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import jdatetime
from django.conf import settings
from django.utils import timezone

JALALI_DATE_FORMAT = "%Y-%m-%d"
JALALI_DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def get_local_timezone() -> ZoneInfo:
    """Return the default timezone configured for the project."""

    return ZoneInfo(settings.TIME_ZONE)


def ensure_aware(dt: datetime) -> datetime:
    """Ensure the provided datetime is timezone aware."""

    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone=get_local_timezone())
    return dt


def to_jalali_datetime(dt: datetime) -> jdatetime.datetime:
    """Convert a Gregorian datetime to its Jalali counterpart."""

    aware_dt = ensure_aware(dt)
    local_dt = timezone.localtime(aware_dt, timezone=get_local_timezone())
    return jdatetime.datetime.fromgregorian(datetime=local_dt)


def format_jalali(dt: datetime | None, fmt: str = JALALI_DATETIME_FORMAT) -> str | None:
    """Format the supplied datetime as a Jalali string."""

    if dt is None:
        return None

    jalali_dt = to_jalali_datetime(dt)
    return jalali_dt.strftime(fmt)


def format_jalali_date(value: date | None, fmt: str = JALALI_DATE_FORMAT) -> str | None:
    """Format the supplied date as a Jalali string."""

    if value is None:
        return None

    jalali_date = jdatetime.date.fromgregorian(date=value)
    return jalali_date.strftime(fmt)


def parse_jalali(
    value: str,
    fmt: str = JALALI_DATETIME_FORMAT,
    tz: ZoneInfo | None = None,
) -> datetime:
    """Parse a Jalali datetime string into an aware datetime."""

    jalali_dt = jdatetime.datetime.strptime(value, fmt)
    gregorian_dt = jalali_dt.togregorian()
    tzinfo = tz or get_local_timezone()
    if timezone.is_naive(gregorian_dt):
        gregorian_dt = timezone.make_aware(gregorian_dt, timezone=tzinfo)
    return timezone.localtime(gregorian_dt, timezone=tzinfo)
