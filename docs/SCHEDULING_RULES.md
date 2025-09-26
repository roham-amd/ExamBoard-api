# Scheduling Rules

This document captures the authoritative constraints that govern exam
allocations. Each rule is enforced at the model layer (`ExamAllocation.clean`) and
revalidated through the public API to ensure race-safe behaviour during
concurrent bookings.

## Capacity Guard

For every room we maintain a running ledger of seat allocations across all
overlapping windows. The invariant is:

> At any instant `t`, the sum of `allocated_seats` for allocations where
> `start_at <= t < end_at` must be **≤** `room.capacity`.

Because overlapping reservations are permitted, a simple aggregate check is not
sufficient. Instead we perform a sweep-line evaluation (see
[`docs/CAPACITY_LEDGER.md`](./CAPACITY_LEDGER.md)) to detect overflow while the
transaction holds row locks on the affected allocations.

### Examples

- **Allowed**: Room capacity 100 with two overlapping allocations of 50 seats
  each between 09:00–11:00. Ledger peaks at 100, which is within the limit.
- **Rejected**: Same room receives an additional overlapping request for
  10 seats. Ledger would reach 110, so validation fails with a Farsi error
  message explaining the capacity breach.

## Calendar Guards

### Term Window

Every allocation must fall inside the owning exam's term range (inclusive).
The validation compares the localised start and end times against the term's
`start_date`/`end_date` to catch cross-term bookings.

### Blackout Windows

`BlackoutWindow` records define hard scheduling exclusions. They can target a
specific room or apply campus-wide (`room` = `NULL`). Any overlap with the
allocation window leads to immediate rejection.

### Holidays

`Holiday` entries mark all-day closures. An allocation that touches any date in
that range is disallowed, even if the holiday spans multiple days. The
validation normalises the end timestamp (minus one microsecond) so midnight
endpoints still count as part of the same day.

## Transactions & Concurrency

When saving an allocation we wrap the operation in `transaction.atomic()` and
lock all overlapping allocations via `SELECT ... FOR UPDATE`. This ensures that
parallel requests evaluate the ledger against a stable snapshot and prevents
lost updates when bookings compete for the same seats.

## Testing

`apps/exams/tests/test_api.py` exercises the API surface to prove the rules:

- Balanced overlapping allocations within capacity succeed.
- A third overlapping allocation that would overflow capacity fails.
- Blackout windows, holidays, and term boundaries each block conflicting
  requests with Farsi error messages.
