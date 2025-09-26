# Capacity Ledger Algorithm

Overlapping exam allocations are legal as long as the combined seat demand does
not exceed the room capacity at any point in time. To enforce this efficiently
we use a sweep-line approach that converts allocation windows into discrete
"events".

## Event Construction

For each allocation `(start_at, end_at, allocated_seats)` we emit two events:

1. `(start_at, +allocated_seats)` – seats become occupied.
2. `(end_at, -allocated_seats)` – seats are released.

The candidate allocation under validation contributes its own pair of events.

Events are sorted by timestamp. When timestamps match we process departures
(first negative delta) before arrivals to prevent boundary cases (e.g. an exam
ending at 10:00 and another starting at 10:00) from falsely overlapping.

## Ledger Sweep

Iterating through the ordered events we maintain a running counter:

```python
current_load = 0
for timestamp, delta in events:
    current_load += delta
    if current_load > room.capacity:
        raise ValidationError("ظرفیت اتاق در این بازه زمانی تکمیل است.")
```

Because the validation runs inside a transaction with all overlapping rows locked
(`SELECT ... FOR UPDATE`), concurrent requests observe a consistent snapshot of
the ledger. The algorithm runs in `O(n log n)` time for `n` overlapping
allocations, dominated by the sort. In practice the overlapping set is small,
so the check is fast even under contention.

## Worked Example

Consider a room with capacity 100 and three allocation requests:

| Exam | Window (UTC)         | Seats |
| ---- | -------------------- | ----- |
| A    | 09:00 – 11:00        | 50    |
| B    | 10:00 – 12:00        | 50    |
| C    | 10:30 – 11:30        | 10    |

Events after sorting (departures first on ties):

| Timestamp | Δ Seats | Running Total |
| --------- | ------- | ------------- |
| 09:00     | +50     | 50            |
| 10:00     | +50     | 100           |
| 10:30     | +10     | 110 ⟶ **overflow** |

The third request pushes the ledger over capacity, so the API rejects it with a
400 response. The accompanying test case in
`apps/exams/tests/test_api.py::test_capacity_ledger_rejects_overflow` asserts the
behaviour.
