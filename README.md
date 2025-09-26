# ExamBoard API

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-lightgrey)](#)
[![Coverage](https://img.shields.io/badge/Coverage-%E2%89%A590%25-blue)](#)

Backend service for managing exam schedules and related workflows. This repository ships a Django REST framework stack with ready-to-use tooling for local development, testing, and deployment.

## Quick start

### 1. Prerequisites
- Python 3.13 with [uv](https://docs.astral.sh/uv/)
- Docker & Docker Compose
- Make (optional but recommended)

### 2. Local setup
```bash
uv sync --dev
cp src/.env.example src/.env  # customize if needed
uv run python src/manage.py migrate
uv run python src/manage.py runserver 0.0.0.0:8000
```

### 3. Docker Compose
```bash
docker compose up --build -d
# Visit http://localhost:8000/api/health/
```

The Compose stack starts Django and PostgreSQL (with an optional Redis profile for future caching work).

## API health
A placeholder health check lives at `/api/health/` and returns `{"status": "ok"}`.

## Technology stack
- **Django** 5.x with timezone-aware configuration (Asia/Tehran)
- **Django REST framework** with JWT auth (SimpleJWT)
- **drf-spectacular** for OpenAPI schemas and Swagger UI
- **PostgreSQL 16** (via Docker Compose)
- **pytest**, **ruff**, **black**, **isort**, and **pre-commit** for testing and linting
- **uv** for dependency management and virtual environments

## Conventions
- All times are stored in UTC in the database; conversions to Jalali will happen at the API boundaries (see `docs/ADR-000-time-representation.md`).
- Persian (`fa-IR`) is the default locale; ensure UI-facing strings are localized.
- Run `make fmt` and `make lint` before pushing changes.

## Useful commands
| Command | Description |
| --- | --- |
| `make setup` | Install dependencies with dev extras |
| `make fmt` | Format code using black and isort |
| `make lint` | Run ruff, black (check), isort (check-only), and mypy |
| `make test` | Execute the pytest suite |
| `make compose-up` | Start the Docker Compose stack |
| `make compose-down` | Stop the Docker Compose stack |

## Testing & quality gates

- `make test` runs `pytest` with coverage instrumentation and will fail if
  core scheduling modules drop below 90% statement coverage.
- `uv run pytest --cov=apps.exams.models --cov=apps.exams.serializers --cov=apps.exams.views --cov=apps.exams.filters --cov-report=term-missing`
  prints the detailed coverage table used by CI.
- `uv run mypy src/apps/common` enforces strict typing on the shared utilities
  used by validators and serializers.
- `uv run pre-commit run --all-files` executes the complete formatting and
  linting toolchain.

## Additional documentation
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [Local development guide](docs/LOCAL_DEV.md)
- [Architecture overview](docs/ARCHITECTURE.md)
- [Decision log](docs/DECISIONS.md)

