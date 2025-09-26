# Date & Time Handling

The ExamBoard API persists all timestamps in UTC while presenting both Gregorian
and Jalali views to clients. This document outlines the helper utilities,
serializer field, and testing strategy introduced in Phase 2.

## Utilities

The module `apps.common.jalali` exposes a handful of helpers around the
[`jdatetime`](https://github.com/slashmili/python-jalali) library:

| Function | Purpose |
| --- | --- |
| `format_jalali(dt)` | Convert an aware `datetime` into a formatted Jalali string (`YYYY-MM-DD HH:MM`). |
| `parse_jalali(text)` | Parse a Jalali string back to an aware `datetime` in the project default timezone. |
| `to_jalali_datetime(dt)` | Return the underlying `jdatetime.datetime` instance for advanced consumers. |

All helpers normalise input datetimes to the configured timezone (`Asia/Tehran`),
so conversions remain deterministic regardless of the origin timezone.

## Serializer Field

`apps.common.serializers.JalaliDateTimeField` extends DRF's `DateTimeField` to
present both representations when serialising:

```json
{
  "iso": "2025-07-01T08:00:00Z",
  "jalali": "1404-04-10 11:30"
}
```

Input continues to accept ISO-8601 values, ensuring backwards compatibility with
existing clients. Validation errors surface in Farsi to align with the API's
locale (`ساختار تاریخ و زمان معتبر نیست.` when parsing fails).

## Edge Cases & DST

Iran currently keeps clocks at UTC+03:30 year-round, yet the conversion
functions still rely on the configured timezone. Should daylight saving rules
change in the future, the helpers will automatically respect the updated TZ
data through `zoneinfo`.

Round-trip tests cover historical dates around the previous DST cut-over window
(March 20th) to guard against regressions when timezone rules shift.

## Testing Notes

Unit tests reside under `apps/common/tests/` and assert:

- Gregorian → Jalali → Gregorian round-trips remain stable across sample dates.
- The custom serializer field emits the dual representation and validates ISO
  input correctly.
- Error messages returned from the field surface in Farsi.

Whenever the timezone configuration or formatting rules evolve, update the test
fixtures and rerun `make test` to confirm the behaviour.
