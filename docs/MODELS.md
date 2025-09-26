# Domain Models

This document describes the data model backing the scheduling capabilities.

## Mixins
- **TimeStampedModel**: adds `created_at` and `updated_at` timestamps.
- **UserAuditModel**: adds nullable `created_by` / `updated_by` relations to `AUTH_USER_MODEL`.

## Term
- `name`: human readable label.
- `code`: unique slug/code for the term.
- `start_date` / `end_date`: inclusive date boundaries.
- `is_published`: flag indicating visibility to stakeholders.
- `is_archived`: flag indicating whether the term is immutable.
- **Invariants**: `start_date <= end_date`, `code` unique.

## Room
- `name`: unique room identifier.
- `capacity`: positive integer defining available seats.
- `features`: optional JSON blob (e.g., accessibility hints, equipment list).
- **Invariants**: `capacity >= 1`, `name` unique.

## Exam
- `title`: display name for the exam.
- `course_code`: curriculum identifier (unique per term).
- `owner`: staff user responsible for the exam.
- `expected_students`: positive count of registered students.
- `duration_minutes`: positive duration, defaults to 60.
- `term`: associated academic term.
- **Invariants**: `expected_students >= 1`, `duration_minutes >= 1`,
  (`course_code`, `term`) unique together.

## ExamAllocation
- `exam`: scheduled exam instance.
- `room`: allocated room.
- `start_at` / `end_at`: timezone-aware boundaries of the sitting.
- `allocated_seats`: positive seat count committed to the exam.
- **Invariants**: `start_at < end_at`, `allocated_seats >= 1`.

## BlackoutWindow
- `name`: label for the restriction window.
- `start_at` / `end_at`: timezone-aware closure range.
- `room`: optional room scope (null => applies to all rooms).
- `created_by` / `updated_by`: auditing fields for staff ownership.
- **Invariants**: `start_at < end_at`.

## Holiday
- `name`: descriptive name.
- `start_date` / `end_date`: inclusive all-day range.
- **Invariants**: `start_date <= end_date`.
