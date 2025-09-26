"""Routing for the exams API."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import ExamAllocationViewSet

router = DefaultRouter()
router.register(r"exams/allocations", ExamAllocationViewSet, basename="exam-allocation")

urlpatterns = router.urls
