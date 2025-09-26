"""Populate the database with a realistic scheduling dataset."""

from __future__ import annotations

import datetime as dt
import os
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.common.permissions import (
    ADMIN_GROUP,
    INSTRUCTOR_GROUP,
    SCHEDULER_GROUP,
    STUDENT_GROUP,
)
from apps.exams.models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


def aware_datetime(
    year: int, month: int, day: int, hour: int, minute: int = 0
) -> dt.datetime:
    """Build a timezone-aware datetime in UTC for scheduling."""

    return dt.datetime(year, month, day, hour, minute, tzinfo=dt.UTC)


class Command(BaseCommand):
    """Load demo scheduling data for local exploration and tests."""

    help = (
        "Load a published term with rooms, exams, allocations, holidays, "
        "and demo users."
    )

    def handle(self, *args, **options):  # noqa: D401, ANN001
        with transaction.atomic():
            groups = self._ensure_groups()
            users = self._ensure_users(groups)
            term = self._ensure_term()
            rooms = self._ensure_rooms()
            self._ensure_holidays(term)
            self._ensure_blackouts(users["scheduler"], rooms)
            exams = self._ensure_exams(term, users["instructors"])
            self._ensure_allocations(exams, rooms)

        self.stdout.write(self.style.SUCCESS("Demo data loaded successfully."))

    # Creation helpers -------------------------------------------------

    def _ensure_groups(self) -> dict[str, Group]:
        groups: dict[str, Group] = {}
        for name in (ADMIN_GROUP, SCHEDULER_GROUP, INSTRUCTOR_GROUP, STUDENT_GROUP):
            group, _ = Group.objects.get_or_create(name=name)
            groups[name] = group
        return groups

    def _ensure_users(self, groups: dict[str, Group]) -> dict[str, object]:
        User = get_user_model()

        passwords = {
            ADMIN_GROUP: os.getenv("DEMO_ADMIN_PASSWORD", "admin-pass"),
            SCHEDULER_GROUP: os.getenv("DEMO_SCHEDULER_PASSWORD", "scheduler-pass"),
            INSTRUCTOR_GROUP: os.getenv("DEMO_INSTRUCTOR_PASSWORD", "instructor-pass"),
            STUDENT_GROUP: os.getenv("DEMO_STUDENT_PASSWORD", "student-pass"),
        }

        demo_users = [
            {
                "username": "admin_demo",
                "email": "admin@example.com",
                "group": ADMIN_GROUP,
                "first_name": "ادمین",
                "last_name": "نمونه",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "scheduler_demo",
                "email": "scheduler@example.com",
                "group": SCHEDULER_GROUP,
                "first_name": "زمان‌بند",
                "last_name": "نمونه",
                "is_staff": True,
                "is_superuser": False,
            },
            {
                "username": "student_demo",
                "email": "student@example.com",
                "group": STUDENT_GROUP,
                "first_name": "دانشجو",
                "last_name": "نمونه",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        created_users: dict[str, list] = defaultdict(list)

        for config in demo_users:
            group_name = config["group"]
            defaults = {
                "email": config["email"],
                "first_name": config["first_name"],
                "last_name": config["last_name"],
                "is_staff": config["is_staff"],
                "is_superuser": config["is_superuser"],
            }
            user, created = User.objects.get_or_create(
                username=config["username"], defaults=defaults
            )
            if not created:
                for field, value in defaults.items():
                    setattr(user, field, value)
            user.set_password(passwords[group_name])
            user.save()
            user.groups.add(groups[group_name])
            created_users[group_name].append(user)

        instructor_configs = [
            {
                "username": "instructor_rahimi",
                "email": "rahimi@example.com",
                "first_name": "دکتر",
                "last_name": "رحیمی",
            },
            {
                "username": "instructor_moradi",
                "email": "moradi@example.com",
                "first_name": "دکتر",
                "last_name": "مرادی",
            },
        ]

        instructors = []
        for config in instructor_configs:
            user, created = User.objects.get_or_create(
                username=config["username"],
                defaults={
                    "email": config["email"],
                    "first_name": config["first_name"],
                    "last_name": config["last_name"],
                    "is_staff": True,
                },
            )
            if not created:
                user.email = config["email"]
                user.first_name = config["first_name"]
                user.last_name = config["last_name"]
                user.is_staff = True
            user.set_password(passwords[INSTRUCTOR_GROUP])
            user.save()
            user.groups.add(groups[INSTRUCTOR_GROUP])
            instructors.append(user)

        created_users[INSTRUCTOR_GROUP] = instructors

        return {
            "admin": created_users[ADMIN_GROUP][0],
            "scheduler": created_users[SCHEDULER_GROUP][0],
            "student": created_users[STUDENT_GROUP][0],
            "instructors": instructors,
        }

    def _ensure_term(self) -> Term:
        term_defaults = {
            "name": "پاییز ۱۴۰۳",
            "start_date": dt.date(2024, 9, 1),
            "end_date": dt.date(2025, 1, 15),
            "is_published": True,
        }
        term, created = Term.objects.get_or_create(
            code="1403-FA", defaults=term_defaults
        )
        if term.name != term_defaults["name"]:
            term.name = term_defaults["name"]
            term.save(update_fields=["name", "updated_at"])
        if created or not term.is_published:
            term.publish()
        return term

    def _ensure_rooms(self) -> dict[str, Room]:
        rooms_data = [
            ("Main Hall", 150, {"type": "hall", "av": True}),
            ("North Auditorium", 120, {"type": "auditorium", "av": True}),
            ("Physics Lab", 60, {"type": "lab", "special_equipment": True}),
            ("Chemistry Lab", 60, {"type": "lab", "fume_hood": True}),
            ("Lecture Theatre A", 90, {"type": "theatre", "av": True}),
        ]

        room_objects: dict[str, Room] = {}
        for name, capacity, features in rooms_data:
            room, _ = Room.objects.update_or_create(
                name=name,
                defaults={"capacity": capacity, "features": features},
            )
            room_objects[name] = room

        return room_objects

    def _ensure_holidays(self, term: Term) -> None:
        holidays = [
            ("تعطیلات میان‌ترم", dt.date(2024, 10, 24), dt.date(2024, 10, 26)),
            ("شب یلدا", dt.date(2024, 12, 20), dt.date(2024, 12, 21)),
        ]

        for name, start, end in holidays:
            Holiday.objects.update_or_create(
                name=name,
                defaults={"start_date": start, "end_date": end},
            )

    def _ensure_blackouts(
        self, scheduler, rooms: dict[str, Room]
    ) -> None:  # noqa: ANN001 - admin user type
        blackouts = [
            {
                "name": "نصب سامانه تهویه",
                "start_at": aware_datetime(2024, 11, 5, 6, 0),
                "end_at": aware_datetime(2024, 11, 5, 12, 0),
                "room": None,
            },
            {
                "name": "کالیبراسیون آزمایشگاه فیزیک",
                "start_at": aware_datetime(2024, 11, 20, 7, 0),
                "end_at": aware_datetime(2024, 11, 20, 12, 0),
                "room": rooms["Physics Lab"],
            },
        ]

        for data in blackouts:
            defaults = {
                "start_at": data["start_at"],
                "end_at": data["end_at"],
                "room": data["room"],
                "created_by": scheduler,
                "updated_by": scheduler,
            }
            BlackoutWindow.objects.update_or_create(
                name=data["name"], defaults=defaults
            )

    def _ensure_exams(
        self, term: Term, instructors
    ) -> dict[str, Exam]:  # noqa: ANN001 - iterable
        instructors = list(instructors)
        exams_data = [
            {
                "title": "الگوریتم‌های پیشرفته",
                "course_code": "CS501",
                "expected_students": 160,
                "duration_minutes": 120,
            },
            {
                "title": "پایگاه‌داده‌ها",
                "course_code": "CS341",
                "expected_students": 140,
                "duration_minutes": 120,
            },
            {
                "title": "جبر خطی ۲",
                "course_code": "MATH220",
                "expected_students": 90,
                "duration_minutes": 90,
            },
            {
                "title": "ترمودینامیک",
                "course_code": "ME210",
                "expected_students": 70,
                "duration_minutes": 120,
            },
            {
                "title": "منطق دیجیتال",
                "course_code": "EE130",
                "expected_students": 80,
                "duration_minutes": 90,
            },
            {
                "title": "ادبیات فارسی",
                "course_code": "HUM101",
                "expected_students": 60,
                "duration_minutes": 90,
            },
            {
                "title": "احتمال مهندسی",
                "course_code": "STAT210",
                "expected_students": 120,
                "duration_minutes": 120,
            },
            {
                "title": "سیستم‌عامل‌ها",
                "course_code": "CS302",
                "expected_students": 130,
                "duration_minutes": 120,
            },
            {
                "title": "سیگنال‌ها و سیستم‌ها",
                "course_code": "EE250",
                "expected_students": 75,
                "duration_minutes": 120,
            },
            {
                "title": "تحلیل عددی",
                "course_code": "MATH330",
                "expected_students": 85,
                "duration_minutes": 90,
            },
        ]

        exam_objects: dict[str, Exam] = {}
        for index, data in enumerate(exams_data):
            owner = instructors[index % len(instructors)]
            defaults = {
                "title": data["title"],
                "owner": owner,
                "expected_students": data["expected_students"],
                "duration_minutes": data["duration_minutes"],
            }
            exam, _ = Exam.objects.update_or_create(
                term=term,
                course_code=data["course_code"],
                defaults=defaults,
            )
            exam_objects[data["course_code"]] = exam

        return exam_objects

    def _ensure_allocations(
        self, exams: dict[str, Exam], rooms: dict[str, Room]
    ) -> None:
        schedule = [
            ("CS501", "Main Hall", aware_datetime(2024, 10, 7, 8, 0), 90),
            ("CS501", "North Auditorium", aware_datetime(2024, 10, 7, 8, 0), 70),
            ("CS341", "Main Hall", aware_datetime(2024, 10, 8, 9, 0), 120),
            ("MATH220", "Lecture Theatre A", aware_datetime(2024, 10, 8, 9, 30), 60),
            ("MATH220", "Physics Lab", aware_datetime(2024, 10, 8, 9, 30), 30),
            ("ME210", "North Auditorium", aware_datetime(2024, 10, 9, 7, 30), 70),
            ("EE130", "Physics Lab", aware_datetime(2024, 10, 9, 10, 0), 40),
            ("EE130", "Chemistry Lab", aware_datetime(2024, 10, 9, 10, 0), 40),
            ("HUM101", "Lecture Theatre A", aware_datetime(2024, 10, 10, 8, 0), 60),
            ("STAT210", "Main Hall", aware_datetime(2024, 10, 10, 9, 0), 110),
            ("EE250", "Main Hall", aware_datetime(2024, 10, 10, 10, 0), 35),
            ("CS302", "North Auditorium", aware_datetime(2024, 10, 11, 8, 0), 80),
            ("CS302", "Lecture Theatre A", aware_datetime(2024, 10, 11, 8, 0), 50),
            ("MATH330", "Lecture Theatre A", aware_datetime(2024, 10, 12, 8, 30), 85),
            ("STAT210", "Main Hall", aware_datetime(2024, 11, 3, 8, 0), 100),
            ("CS341", "Main Hall", aware_datetime(2024, 11, 3, 10, 30), 80),
            ("ME210", "North Auditorium", aware_datetime(2024, 11, 4, 9, 0), 60),
            ("HUM101", "Lecture Theatre A", aware_datetime(2024, 11, 4, 11, 0), 55),
            ("EE250", "Chemistry Lab", aware_datetime(2024, 11, 6, 8, 0), 40),
            ("CS501", "Main Hall", aware_datetime(2024, 12, 10, 8, 0), 90),
        ]

        for course_code, room_name, start_at, seats in schedule:
            exam = exams[course_code]
            room = rooms[room_name]
            duration = dt.timedelta(minutes=exam.duration_minutes)
            end_at = start_at + duration

            ExamAllocation.objects.update_or_create(
                exam=exam,
                room=room,
                start_at=start_at,
                defaults={
                    "end_at": end_at,
                    "allocated_seats": seats,
                },
            )
