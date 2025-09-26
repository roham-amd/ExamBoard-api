# ADR-000: Time Representation

## Status
Accepted

## Context
Exam dates must be consistent across distributed systems and integrations. Users interact with the platform primarily in Iran, where the local time zone is Asia/Tehran and the Jalali calendar is standard for communication. The backend stores timestamps in PostgreSQL and exchanges data through the REST API.

## Decision
- Persist all timestamps in the database as timezone-aware UTC values (`USE_TZ = True`).
- Convert timestamps to the Jalali calendar at the API boundary (serializers, response helpers) before returning them to clients.
- Accept incoming timestamps in Jalali + Asia/Tehran by default and normalize them to UTC before persistence.
- Document all time-handling rules in API schemas and developer guides to avoid ambiguity.

## Consequences
- Database operations remain stable regardless of daylight saving changes in Iran.
- Client applications receive culturally appropriate timestamps while integrations can negotiate UTC when needed.
- Additional serializer utilities are required to perform Jalali conversions; these utilities should be covered by tests.
