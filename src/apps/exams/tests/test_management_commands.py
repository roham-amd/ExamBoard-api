"""Tests for the demo data management command."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.common.permissions import (
    ADMIN_GROUP,
    INSTRUCTOR_GROUP,
    SCHEDULER_GROUP,
    STUDENT_GROUP,
)
from apps.exams.models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


@pytest.mark.django_db
def test_load_demo_data_creates_expected_entities() -> None:
    call_command("load_demo_data")

    term = Term.objects.get(code="1403-FA")
    assert term.is_published

    assert Room.objects.count() == 5
    assert Exam.objects.count() == 10
    assert ExamAllocation.objects.count() == 20
    assert Holiday.objects.count() == 2
    assert BlackoutWindow.objects.count() == 2

    User = get_user_model()
    admin = User.objects.get(username="admin_demo")
    scheduler = User.objects.get(username="scheduler_demo")
    instructor = User.objects.get(username="instructor_rahimi")
    student = User.objects.get(username="student_demo")

    assert admin.groups.filter(name=ADMIN_GROUP).exists()
    assert scheduler.groups.filter(name=SCHEDULER_GROUP).exists()
    assert instructor.groups.filter(name=INSTRUCTOR_GROUP).exists()
    assert student.groups.filter(name=STUDENT_GROUP).exists()


@pytest.mark.django_db
def test_load_demo_data_is_idempotent() -> None:
    call_command("load_demo_data")
    first_allocation_ids = set(
        ExamAllocation.objects.values_list(
            "exam__course_code", "room__name", "start_at"
        )
    )

    call_command("load_demo_data")

    second_allocation_ids = set(
        ExamAllocation.objects.values_list(
            "exam__course_code", "room__name", "start_at"
        )
    )

    assert first_allocation_ids == second_allocation_ids
    assert ExamAllocation.objects.count() == 20

    for name in (ADMIN_GROUP, SCHEDULER_GROUP, INSTRUCTOR_GROUP, STUDENT_GROUP):
        assert Group.objects.filter(name=name).count() == 1
