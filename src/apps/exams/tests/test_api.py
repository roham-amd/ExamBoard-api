import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.exams.models import BlackoutWindow, Exam, Holiday, Room, Term


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def term():
    return Term.objects.create(
        name="Spring 1403",
        code="1403-SPR",
        start_date=dt.date(2024, 3, 20),
        end_date=dt.date(2024, 6, 20),
    )


@pytest.fixture
def room():
    return Room.objects.create(name="Auditorium", capacity=100)


@pytest.fixture
def exam(term):
    User = get_user_model()
    owner = User.objects.create_user(username="owner", password="secret123")
    return Exam.objects.create(
        title="Linear Algebra",
        course_code="MATH201",
        owner=owner,
        expected_students=80,
        term=term,
    )


@pytest.mark.django_db
class TestExamAllocationAPI:
    endpoint = "/api/exams/allocations/"

    def test_capacity_ledger_accepts_balanced_overlap(self, api_client, exam, room):
        first = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 4, 10, 8, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 4, 10, 10, 0, tzinfo=dt.UTC).isoformat(),
            "allocated_seats": 50,
        }
        second = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 4, 10, 9, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 4, 10, 11, 0, tzinfo=dt.UTC).isoformat(),
            "allocated_seats": 50,
        }
        response_one = api_client.post(self.endpoint, first, format="json")
        response_two = api_client.post(self.endpoint, second, format="json")

        assert response_one.status_code == 201
        assert response_two.status_code == 201

    def test_capacity_ledger_rejects_overflow(self, api_client, exam, room):
        base_payload = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 4, 11, 8, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 4, 11, 10, 0, tzinfo=dt.UTC).isoformat(),
        }

        ok_one = {**base_payload, "allocated_seats": 50}
        ok_two = {**base_payload, "allocated_seats": 40}
        fail_payload = {**base_payload, "allocated_seats": 20}

        api_client.post(self.endpoint, ok_one, format="json")
        api_client.post(self.endpoint, ok_two, format="json")
        response = api_client.post(self.endpoint, fail_payload, format="json")

        assert response.status_code == 400
        assert "allocated_seats" in response.json()

    def test_blackout_blocks_allocation(self, api_client, exam, room):
        BlackoutWindow.objects.create(
            name="Maintenance",
            start_at=dt.datetime(2024, 4, 15, 8, 0, tzinfo=dt.UTC),
            end_at=dt.datetime(2024, 4, 15, 12, 0, tzinfo=dt.UTC),
            room=room,
        )

        payload = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 4, 15, 9, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 4, 15, 10, 0, tzinfo=dt.UTC).isoformat(),
            "allocated_seats": 10,
        }

        response = api_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 400
        assert "start_at" in response.json()

    def test_allocation_must_reside_within_term(self, api_client, exam, room):
        payload = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 7, 1, 8, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 7, 1, 10, 0, tzinfo=dt.UTC).isoformat(),
            "allocated_seats": 10,
        }

        response = api_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 400
        assert "start_at" in response.json()

    def test_holiday_blocks_allocation(self, api_client, exam, room):
        Holiday.objects.create(
            name="Nowruz",
            start_date=dt.date(2024, 3, 20),
            end_date=dt.date(2024, 3, 23),
        )

        payload = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 3, 21, 8, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 3, 21, 10, 0, tzinfo=dt.UTC).isoformat(),
            "allocated_seats": 10,
        }

        response = api_client.post(self.endpoint, payload, format="json")

        assert response.status_code == 400
        assert "start_at" in response.json()
