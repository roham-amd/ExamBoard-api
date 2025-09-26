# Local Development

## Install dependencies
```bash
uv sync --dev
cp src/.env.example src/.env
```

## Database
Use the included PostgreSQL container or point `DATABASE_URL` to an existing instance.

### Docker Compose workflow
```bash
make compose-up
make migrate
```

Stop services when done:
```bash
make compose-down
```

## Running the app
```bash
make runserver
```
Visit [http://localhost:8000/api/health/](http://localhost:8000/api/health/) for a quick check.

## Quality gates
```bash
make fmt
make lint
make test
```

## Pre-commit
Install hooks once:
```bash
uv run pre-commit install
```
Hooks run automatically on staged files. Trigger them manually with:
```bash
uv run pre-commit run --all-files
```

## Tests
Pytest is configured with Django support (`pytest-django`). Add tests under `apps/<app-name>/tests/`.
