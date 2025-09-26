"""Routing for the exams API."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BlackoutWindowViewSet,
    ExamAllocationViewSet,
    ExamViewSet,
    HolidayViewSet,
    PublicTimetableView,
    RoomViewSet,
    TermViewSet,
)

router = DefaultRouter()
router.register(r"terms", TermViewSet, basename="term")
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"exams", ExamViewSet, basename="exam")
router.register(r"allocations", ExamAllocationViewSet, basename="allocation")
router.register(r"blackouts", BlackoutWindowViewSet, basename="blackout")
router.register(r"holidays", HolidayViewSet, basename="holiday")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "public/terms/<int:term_id>/timetable/",
        PublicTimetableView.as_view(),
        name="public-term-timetable",
    ),
]
