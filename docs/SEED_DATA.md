# Demo Data Catalogue

The `load_demo_data` management command seeds the database with a published term,
rooms, exams, allocations, and demo users so local environments have a realistic
schedule to explore.

## Running the command

```bash
uv run python src/manage.py load_demo_data
```

The command is idempotent — running it multiple times keeps the dataset
synchronized with the definitions below.

## Created objects

| Category | Details |
| --- | --- |
| Term | `پاییز ۱۴۰۳` (`1403-FA`), 1 شهریور 1403 تا 25 دی 1403، منتشر شده |
| Rooms | Main Hall, North Auditorium, Physics Lab, Chemistry Lab, Lecture Theatre A |
| Exams | 10 courses spanning engineering, science, and humanities departments |
| Allocations | 20 slots including capacity-balanced overlaps and multi-room sittings |
| Holidays | میان‌ترم (24–26 مهر 1403) و شب یلدا (30 آذر–1 دی 1403) |
| Blackouts | سامانه تهویه (15 آبان 1403) و کالیبراسیون آزمایشگاه فیزیک (30 آبان 1403) |

Allocations cover weekday and weekend patterns, enforce blackout and holiday
constraints, and demonstrate multi-room splits for large cohorts.

## Demo accounts

Passwords come from `.env` values so teams can override them without editing
source. The `.env.example` file ships with sensible defaults:

| Username | Role | Password env var | Default |
| --- | --- | --- | --- |
| `admin_demo` | Admin | `DEMO_ADMIN_PASSWORD` | `admin-pass` |
| `scheduler_demo` | Scheduler | `DEMO_SCHEDULER_PASSWORD` | `scheduler-pass` |
| `instructor_rahimi` / `instructor_moradi` | Instructor | `DEMO_INSTRUCTOR_PASSWORD` | `instructor-pass` |
| `student_demo` | Student | `DEMO_STUDENT_PASSWORD` | `student-pass` |

All demo staff accounts are enabled for the Django admin. The admin user is also
a superuser so it can manage permissions and inspect data quickly.
