"""Integration tests for the scheduling REST API."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.exams.models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def ensure_groups(db):  # noqa: ANN001 - pytest signature
    for name in ("Admin", "Scheduler", "Instructor", "Student"):
        Group.objects.get_or_create(name=name)


@pytest.fixture
def scheduler_user():  # noqa: ANN001 - pytest naming convention
    User = get_user_model()
    user = User.objects.create_user("scheduler", password="test-pass")
    user.groups.add(Group.objects.get(name="Scheduler"))
    return user


@pytest.fixture
def admin_user():  # noqa: ANN001
    User = get_user_model()
    user = User.objects.create_user("admin", password="test-pass")
    user.groups.add(Group.objects.get(name="Admin"))
    return user


@pytest.fixture
def instructor_user():  # noqa: ANN001
    User = get_user_model()
    user = User.objects.create_user("instructor", password="test-pass")
    user.groups.add(Group.objects.get(name="Instructor"))
    return user


@pytest.fixture
def term():
    return Term.objects.create(
        name="Spring 1403",
        code="1403-SPR",
        start_date=dt.date(2024, 3, 20),
        end_date=dt.date(2024, 6, 20),
        is_published=True,
    )


@pytest.fixture
def room():
    return Room.objects.create(name="Auditorium", capacity=100)


@pytest.fixture
def exam(term, instructor_user):
    return Exam.objects.create(
        title="Linear Algebra",
        course_code="MATH201",
        owner=instructor_user,
        expected_students=80,
        term=term,
    )


@pytest.fixture
def scheduler_client(api_client, scheduler_user):
    api_client.force_authenticate(user=scheduler_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def instructor_client(api_client, instructor_user):
    api_client.force_authenticate(user=instructor_user)
    return api_client


@pytest.mark.django_db
class TestExamAllocationAPI:
    endpoint = "/api/allocations/"

    def _payload(self, exam, room, start, end, seats):
        return {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "allocated_seats": seats,
        }

    def test_capacity_ledger_accepts_balanced_overlap(
        self, scheduler_client, exam, room
    ):
        first = self._payload(
            exam,
            room,
            dt.datetime(2024, 4, 10, 8, 0, tzinfo=dt.UTC),
            dt.datetime(2024, 4, 10, 10, 0, tzinfo=dt.UTC),
            50,
        )
        second = self._payload(
            exam,
            room,
            dt.datetime(2024, 4, 10, 9, 0, tzinfo=dt.UTC),
            dt.datetime(2024, 4, 10, 11, 0, tzinfo=dt.UTC),
            50,
        )

        response_one = scheduler_client.post(self.endpoint, first, format="json")
        response_two = scheduler_client.post(self.endpoint, second, format="json")

        assert response_one.status_code == status.HTTP_201_CREATED
        assert response_two.status_code == status.HTTP_201_CREATED

    def test_capacity_ledger_rejects_overflow(self, scheduler_client, exam, room):
        base_payload = {
            "exam": exam.pk,
            "room": room.pk,
            "start_at": dt.datetime(2024, 4, 11, 8, 0, tzinfo=dt.UTC).isoformat(),
            "end_at": dt.datetime(2024, 4, 11, 10, 0, tzinfo=dt.UTC).isoformat(),
        }

        ok_one = {**base_payload, "allocated_seats": 50}
        ok_two = {**base_payload, "allocated_seats": 40}
        fail_payload = {**base_payload, "allocated_seats": 20}

        scheduler_client.post(self.endpoint, ok_one, format="json")
        scheduler_client.post(self.endpoint, ok_two, format="json")
        response = scheduler_client.post(self.endpoint, fail_payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "allocated_seats" in response.json()

    def test_blackout_blocks_allocation(self, scheduler_client, exam, room):
        BlackoutWindow.objects.create(
            name="Maintenance",
            start_at=dt.datetime(2024, 4, 15, 8, 0, tzinfo=dt.UTC),
            end_at=dt.datetime(2024, 4, 15, 12, 0, tzinfo=dt.UTC),
            room=room,
        )

        payload = self._payload(
            exam,
            room,
            dt.datetime(2024, 4, 15, 9, 0, tzinfo=dt.UTC),
            dt.datetime(2024, 4, 15, 10, 0, tzinfo=dt.UTC),
            10,
        )

        response = scheduler_client.post(self.endpoint, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_at" in response.json()

    def test_allocation_must_reside_within_term(self, scheduler_client, exam, room):
        payload = self._payload(
            exam,
            room,
            dt.datetime(2024, 7, 1, 8, 0, tzinfo=dt.UTC),
            dt.datetime(2024, 7, 1, 10, 0, tzinfo=dt.UTC),
            10,
        )

        response = scheduler_client.post(self.endpoint, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_at" in response.json()

    def test_holiday_blocks_allocation(self, scheduler_client, exam, room):
        Holiday.objects.create(
            name="Nowruz",
            start_date=dt.date(2024, 3, 20),
            end_date=dt.date(2024, 3, 23),
        )

        payload = self._payload(
            exam,
            room,
            dt.datetime(2024, 3, 21, 8, 0, tzinfo=dt.UTC),
            dt.datetime(2024, 3, 21, 10, 0, tzinfo=dt.UTC),
            10,
        )

        response = scheduler_client.post(self.endpoint, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_at" in response.json()

    def test_unauthenticated_write_is_blocked(self, api_client, exam, room):
        payload = self._payload(
            exam,
            room,
            dt.datetime(2024, 4, 20, 8, 0, tzinfo=dt.UTC),
            dt.datetime(2024, 4, 20, 9, 0, tzinfo=dt.UTC),
            5,
        )

        response = api_client.post(self.endpoint, payload, format="json")

        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }


@pytest.mark.django_db
class TestTermAPI:
    def test_admin_can_publish_term(self, admin_client, term):
        response = admin_client.post(f"/api/terms/{term.pk}/publish/")
        term.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert term.is_published is True

    def test_non_admin_cannot_publish_term(self, scheduler_client, term):
        response = scheduler_client.post(f"/api/terms/{term.pk}/publish/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_published_term_locks_schema_fields(self, admin_client, term):
        admin_client.post(f"/api/terms/{term.pk}/publish/")

        rename_response = admin_client.patch(
            f"/api/terms/{term.pk}/", {"name": "Updated"}, format="json"
        )
        assert rename_response.status_code == status.HTTP_200_OK

        new_start = (term.start_date + dt.timedelta(days=1)).isoformat()
        response = admin_client.patch(
            f"/api/terms/{term.pk}/",
            {"start_date": new_start},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_date" in response.json()


@pytest.mark.django_db
class TestExamAPI:
    def test_instructor_cannot_update_other_exam(
        self, instructor_client, term, instructor_user
    ):
        other_user = get_user_model().objects.create_user("other", password="pass1234")
        exam = Exam.objects.create(
            title="Physics",
            course_code="PHY101",
            owner=other_user,
            expected_students=30,
            term=term,
        )

        payload = {
            "title": "Physics Updated",
            "course_code": "PHY101",
            "owner": other_user.pk,
            "expected_students": 30,
            "duration_minutes": 60,
            "term": term.pk,
        }

        response = instructor_client.put(
            f"/api/exams/{exam.pk}/", payload, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_instructor_owns_created_exam(
        self, instructor_client, term, instructor_user
    ):
        payload = {
            "title": "Chemistry",
            "course_code": "CHEM200",
            "expected_students": 45,
            "duration_minutes": 90,
            "term": term.pk,
        }

        response = instructor_client.post("/api/exams/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        created = Exam.objects.get(pk=response.json()["id"])
        assert created.owner == instructor_user


@pytest.mark.django_db
class TestPublicTimetable:
    def test_public_timetable_returns_allocations(self, term, room, exam):
        start = timezone.make_aware(dt.datetime(2024, 4, 1, 8, 0))
        ExamAllocation.objects.create(
            exam=exam,
            room=room,
            start_at=start,
            end_at=start + dt.timedelta(hours=2),
            allocated_seats=30,
        )

        client = APIClient()
        response = client.get(
            f"/api/public/terms/{term.pk}/timetable/?scope=day&date=2024-04-01"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["term"]["id"] == term.pk
        assert payload["requested_range"]["scope"] == "day"
        assert payload["rooms"][0]["allocations"][0]["allocated_seats"] == 30

    def test_public_timetable_paginates_rooms(self, term, exam):
        term.publish()
        rooms = [
            Room.objects.create(name=f"Room {idx}", capacity=20) for idx in range(3)
        ]
        for room in rooms:
            ExamAllocation.objects.create(
                exam=exam,
                room=room,
                start_at=timezone.make_aware(dt.datetime(2024, 4, 1, 8, 0)),
                end_at=timezone.make_aware(dt.datetime(2024, 4, 1, 9, 0)),
                allocated_seats=10,
            )

        client = APIClient()
        response = client.get(
            f"/api/public/terms/{term.pk}/timetable/?page_size=1&date=2024-04-01"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["pagination"]["count"] == 3
        assert len(payload["rooms"]) == 1
        assert payload["pagination"]["next"] is not None

    def test_unpublished_term_is_not_visible(self, term):
        term.is_published = False
        term.save(update_fields=["is_published"])

        client = APIClient()
        response = client.get(f"/api/public/terms/{term.pk}/timetable/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
