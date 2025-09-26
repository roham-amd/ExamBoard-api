import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health_returns_ok(self):
        client = APIClient()
        url = reverse("health:health")
        response = client.get(url)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
