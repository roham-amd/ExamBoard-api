from __future__ import annotations

import pytest
from django.db.migrations.executor import MigrationExecutor

from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health_reports_database_and_migrations(self):
        client = APIClient()
        url = reverse("health:health")

        response = client.get(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["database"] == {"status": "ok"}
        assert payload["migrations"] == {"status": "ok", "pending": []}
        assert "timestamp" in payload

    def test_health_marks_pending_migrations(self, monkeypatch):
        client = APIClient()
        url = reverse("health:health")

        def fake_plan(_self, _targets):
            fake_migration = type(
                "Migration", (), {"app_label": "apps", "name": "0002_extra"}
            )
            return [(fake_migration, False)]

        monkeypatch.setattr(MigrationExecutor, "migration_plan", fake_plan)

        response = client.get(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["migrations"] == {
            "status": "pending",
            "pending": ["apps.0002_extra"],
        }
