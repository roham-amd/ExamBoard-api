"""Viewsets for the exam scheduling API."""

from __future__ import annotations

from rest_framework import viewsets

from .models import ExamAllocation
from .serializers import ExamAllocationSerializer


class ExamAllocationViewSet(viewsets.ModelViewSet):
    """API endpoint for managing exam allocations."""

    queryset = ExamAllocation.objects.select_related("exam", "room")
    serializer_class = ExamAllocationSerializer
