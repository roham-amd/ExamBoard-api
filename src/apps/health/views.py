from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(_request):
    """Report application health, database connectivity, and migration status."""

    payload = {
        "status": "ok",
        "timestamp": timezone.now(),
        "database": {"status": "ok"},
        "migrations": {"status": "ok", "pending": []},
    }
    status_code = 200

    try:
        connection.ensure_connection()
    except OperationalError as exc:  # pragma: no cover - defensive branch
        payload["status"] = "error"
        payload["database"] = {
            "status": "error",
            "details": str(exc),
        }
        payload["migrations"] = {"status": "unknown", "pending": []}
        status_code = 503
    else:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = [
                f"{migration.app_label}.{migration.name}" for migration, _ in plan
            ]
            payload["status"] = "degraded"
            payload["migrations"] = {"status": "pending", "pending": pending}

    return Response(payload, status=status_code)
