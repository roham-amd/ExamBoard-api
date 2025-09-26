# Capacity Analytics Endpoints

The capacity heatmap endpoint exposes a lightweight aggregate that powers UI
widgets showing how heavily rooms are used during a given term.

## Room capacity heatmap

```
GET /api/rooms/capacity-heatmap/
```

### Query parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `term` | integer | ✓ | Identifier of the academic term to summarise. |
| `start_date` | ISO date | | Optional lower bound (clamped to the term range). |
| `end_date` | ISO date | | Optional upper bound (clamped to the term range). |
| `room` | integer (repeatable) | | Limit the aggregation to specific rooms. |

### Response payload

The API returns term metadata plus an array of rooms. Each room contains one
entry per day in the requested window. Every date is represented with dual ISO
and Jalali values to stay consistent with the rest of the platform.

```json
{
  "term": {
    "id": 5,
    "name": "Spring 1403",
    "code": "1403-SPR",
    "start_date": {"iso": "2024-03-20", "jalali": "1403-01-01"},
    "end_date": {"iso": "2024-06-20", "jalali": "1403-03-31"},
    "is_published": true,
    "is_archived": false
  },
  "start_date": {"iso": "2024-04-10", "jalali": "1403-01-22"},
  "end_date": {"iso": "2024-04-11", "jalali": "1403-01-23"},
  "rooms": [
    {
      "id": 3,
      "name": "Auditorium",
      "capacity": 100,
      "days": [
        {
          "date": {"iso": "2024-04-10", "jalali": "1403-01-22"},
          "peak_allocated_seats": 90,
          "total_allocated_seats": 90,
          "allocation_count": 2,
          "utilisation": 0.9
        }
      ]
    }
  ]
}
```

* `peak_allocated_seats` – maximum concurrent seats booked in that room on the
  specified day.
* `total_allocated_seats` – sum of seats booked across all allocations on that
  day (useful for estimating churn).
* `allocation_count` – number of allocations overlapping that date.
* `utilisation` – peak allocated seats divided by the room capacity (0–1 range).

The endpoint is read-only and available to anonymous consumers so public dashboards
can render usage charts without additional authentication.
