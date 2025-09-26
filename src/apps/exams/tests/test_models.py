import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.exams.models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


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
    return Room.objects.create(name="Main Hall", capacity=120)


@pytest.fixture
def user():
    User = get_user_model()
    return User.objects.create_user(username="owner", password="secret123")


@pytest.mark.django_db
class TestExamModels:
    def test_exam_unique_course_code_per_term(self, term, user):
        Exam.objects.create(
            title="Calculus I",
            course_code="MATH101",
            owner=user,
            expected_students=60,
            term=term,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Exam.objects.create(
                    title="Calculus I - Makeup",
                    course_code="MATH101",
                    owner=user,
                    expected_students=20,
                    term=term,
                )

    def test_exam_allocation_requires_start_before_end(self, term, room, user):
        exam = Exam.objects.create(
            title="Physics",
            course_code="PHY100",
            owner=user,
            expected_students=80,
            term=term,
        )

        with pytest.raises(ValidationError):
            ExamAllocation(
                exam=exam,
                room=room,
                start_at=dt.datetime(2024, 4, 1, 10, 0, tzinfo=dt.UTC),
                end_at=dt.datetime(2024, 4, 1, 9, 0, tzinfo=dt.UTC),
                allocated_seats=50,
            ).full_clean()

    def test_blackout_window_optional_room(self, user):
        blackout = BlackoutWindow.objects.create(
            name="Campus closed",
            start_at=dt.datetime(2024, 4, 5, 8, 0, tzinfo=dt.UTC),
            end_at=dt.datetime(2024, 4, 5, 18, 0, tzinfo=dt.UTC),
            created_by=user,
            updated_by=user,
        )

        assert blackout.room is None

    def test_holiday_range_validation(self):
        Holiday.objects.create(
            name="Nowruz",
            start_date=dt.date(2024, 3, 20),
            end_date=dt.date(2024, 3, 24),
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Holiday.objects.create(
                    name="Invalid",
                    start_date=dt.date(2024, 4, 10),
                    end_date=dt.date(2024, 4, 9),
                )

    def test_term_publish_locks_critical_fields(self, term):
        term.publish()
        term.start_date = term.start_date + dt.timedelta(days=1)

        with pytest.raises(ValidationError):
            term.full_clean()
