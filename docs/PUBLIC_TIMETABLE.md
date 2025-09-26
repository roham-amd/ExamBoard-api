# Public Timetable API

The public timetable exposes a read-only view of published term schedules at
`GET /api/public/terms/{term_id}/timetable/`. Anonymous visitors can inspect the
schedule for a specific term without authentication as soon as the term is
published.

## Request Parameters

| Query Parameter | Description |
| ----------------| ----------- |
| `scope`         | Limits the response to a `day`, `week`, or `month` window. Defaults to `week`. |
| `date`          | ISO-8601 date used as the anchor for `scope`. Defaults to the term start date. |
| `page`          | Optional page number when paginating rooms. |
| `page_size`     | Optional page size for rooms (default 25, max 200). |

The effective range is also clamped to the term's start and end boundaries so a
request outside the term will transparently shrink to the valid period.

## Response Shape

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
  "requested_range": {
    "scope": "week",
    "label": "1403 فروردین 1 تا 1403 فروردین 7",
    "start": {"iso": "2024-03-20T04:30:00Z", "jalali": "1403-01-01 09:00"},
    "end": {"iso": "2024-03-27T04:30:00Z", "jalali": "1403-01-08 09:00"}
  },
  "rooms": [
    {
      "room_id": 12,
      "room_name": "Auditorium",
      "capacity": 120,
      "allocations": [
        {
          "id": 44,
          "exam_title": "Linear Algebra",
          "course_code": "MATH201",
          "start_at": {"iso": "2024-03-21T07:30:00Z", "jalali": "1403-01-02 12:00"},
          "end_at": {"iso": "2024-03-21T09:30:00Z", "jalali": "1403-01-02 14:00"},
          "allocated_seats": 60
        }
      ]
    }
  ],
  "pagination": {
    "count": 3,
    "next": "https://example.test/api/public/terms/5/timetable/?page=2",
    "previous": null
  }
}
```

Times are returned in dual format (`iso` UTC timestamp and human-readable
Jalali label) for every allocation, as well as the requested range boundaries.

## Publishing Workflow

Only administrators may publish a term via `POST /api/terms/{id}/publish/`. Once
published, schema-critical fields (`code`, `start_date`, and `end_date`) are
locked against further edits to keep allocation data consistent with the public
representation. Names and archival flags remain editable so typos can be fixed
without republishing.

## Future Enhancements

* The response can be cached by scope/date pair if load requires it. Django's
  per-view caching middleware or a CDN in front of the API would suffice.
* If we later introduce instructor-specific or course-specific filters we can
  extend the request parameters without breaking existing consumers because the
  response envelope is already explicit about metadata and pagination.
