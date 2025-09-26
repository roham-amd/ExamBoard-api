# Deployment guide

This document summarizes the operational expectations for running ExamBoard in production.

## Environment variables

| Variable | Description | Recommended value |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Cryptographic secret for Django; change per environment. | Use a long random string managed by your secret store. |
| `DJANGO_DEBUG` | Enables Django debug pages. | `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts the API should respond to. | `examboard.example.com` (plus any private load balancer hostnames). |
| `DATABASE_URL` | Connection string for PostgreSQL. | `postgres://examboard:<password>@db:5432/examboard` |
| `REDIS_URL` (future) | Optional cache backend. | Leave unset until caching is enabled. |

Copy `src/.env.example` and adjust each variable before the first deploy.

## First run checklist

1. Build the container image: `docker build -t examboard-api .`.
2. Provision a PostgreSQL 16 database and create the `examboard` role.
3. Supply a `.env` file with the variables above.
4. Start the application using the production profile: `docker compose --profile prod up -d`.
5. Confirm `http(s)://<host>/api/health/` reports a payload with `"status": "ok"`.

The Gunicorn entrypoint automatically applies database migrations and collects static assets via WhiteNoise before serving
traffic.

## Health monitoring

The `/api/health/` endpoint returns:

- `status`: `ok`, `degraded` (pending migrations), or `error` (database unreachable).
- `database`: status details, including exception messages when failures occur.
- `migrations`: the list of pending migration labels, if any.

Configure your load balancer or orchestrator health checks to poll this endpoint.

## Backups and restores

- Schedule regular PostgreSQL dumps using `pg_dump` (e.g., `pg_dump --format=custom examboard > backup.dump`).
- Test restores by replaying the dump into a staging environment: `pg_restore --clean --dbname=examboard backup.dump`.
- Store dumps in an encrypted bucket with rotation policies that match your compliance requirements.

## Scaling notes

- **Vertical scaling**: Increase the CPU/RAM allocated to the container host and tune Gunicorn workers by setting
  `GUNICORN_CMD_ARGS="--workers=<n>"` (the default workers value scales with available CPU cores).
- **Horizontal scaling**: Run multiple containers behind a load balancer. Ensure all instances share the same PostgreSQL
  database and have access to a shared static file cache (WhiteNoise serves static assets from the container image).
- **Background tasks**: Redis is available under the `cache` Compose profile for future asynchronous workers.

## Maintenance mode

To perform disruptive maintenance:

1. Disable the load balancer target(s).
2. Stop the Compose stack: `docker compose --profile prod down`.
3. Run migrations or data patches offline as needed.
4. Re-enable the production stack with `docker compose --profile prod up -d`.
