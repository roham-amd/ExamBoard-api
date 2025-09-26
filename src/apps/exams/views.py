"""Viewsets for the exam scheduling API."""

from __future__ import annotations

import datetime as dt

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import jalali
from apps.common.permissions import (
    AdminOnly,
    AdminSchedulerInstructorWrite,
    AdminSchedulerWrite,
    ReadOnlyForAnonymous,
    user_in_groups,
)

from .filters import (
    BlackoutFilter,
    ExamAllocationFilter,
    ExamFilter,
    HolidayFilter,
    RoomFilter,
    TermFilter,
)
from .models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term
from .serializers import (
    BlackoutWindowSerializer,
    ExamAllocationSerializer,
    ExamSerializer,
    HolidaySerializer,
    RoomSerializer,
    TermSerializer,
    TimetableAllocationSerializer,
    TimetableResponseSerializer,
)


class TermViewSet(viewsets.ModelViewSet):
    """CRUD viewset for academic terms."""

    queryset = Term.objects.all().order_by("-start_date", "code")
    serializer_class = TermSerializer
    filterset_class = TermFilter
    ordering_fields = ["start_date", "code", "name"]
    permission_classes = [ReadOnlyForAnonymous, AdminOnly]

    @action(detail=True, methods=["post"], permission_classes=[AdminOnly])
    def publish(self, request, pk=None):  # noqa: ANN001
        term = self.get_object()
        term.is_published = True
        term.save(update_fields=["is_published"])
        serializer = self.get_serializer(term)
        return Response(serializer.data)


class RoomViewSet(viewsets.ModelViewSet):
    """Manage rooms with read-only access for anonymous users."""

    queryset = Room.objects.all().order_by("name")
    serializer_class = RoomSerializer
    filterset_class = RoomFilter
    ordering_fields = ["name", "capacity"]
    permission_classes = [ReadOnlyForAnonymous, AdminSchedulerWrite]


class ExamViewSet(viewsets.ModelViewSet):
    """Manage exams with owner-aware permissions."""

    queryset = Exam.objects.select_related("term", "owner").all()
    serializer_class = ExamSerializer
    filterset_class = ExamFilter
    ordering_fields = ["title", "course_code", "expected_students"]
    permission_classes = [ReadOnlyForAnonymous, AdminSchedulerInstructorWrite]

    def _is_privileged(self, request):  # noqa: ANN001
        return user_in_groups(
            request.user,
            ("Admin", "Scheduler"),
        )

    def perform_create(self, serializer):
        request = self.request
        if not self._is_privileged(request):
            serializer.save(owner=request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        exam = self.get_object()
        if not self._is_privileged(self.request) and exam.owner != self.request.user:
            raise PermissionDenied("تنها مالک آزمون می‌تواند آن را ویرایش کند.")
        serializer.save()

    def perform_destroy(self, instance):
        if (
            not self._is_privileged(self.request)
            and instance.owner != self.request.user
        ):
            raise PermissionDenied("تنها مالک آزمون می‌تواند آن را حذف کند.")
        instance.delete()


class ExamAllocationViewSet(viewsets.ModelViewSet):
    """API endpoint for managing exam allocations."""

    queryset = ExamAllocation.objects.select_related("exam", "room")
    serializer_class = ExamAllocationSerializer
    filterset_class = ExamAllocationFilter
    ordering_fields = ["start_at", "room__name", "exam__title"]
    permission_classes = [ReadOnlyForAnonymous, AdminSchedulerWrite]

    @extend_schema(
        examples=[
            OpenApiExample(
                "Overlap success",
                request_only=True,
                value={
                    "exam": 1,
                    "room": 2,
                    "start_at": "2025-07-01T08:00:00Z",
                    "end_at": "2025-07-01T09:00:00Z",
                    "allocated_seats": 50,
                },
            ),
            OpenApiExample(
                "Capacity breach",
                response_only=True,
                status_codes=["400"],
                value={
                    "allocated_seats": ["ظرفیت اتاق در این بازه زمانی تکمیل است."],
                },
            ),
        ]
    )
    def create(self, request, *args, **kwargs):  # noqa: ANN001
        return super().create(request, *args, **kwargs)


class BlackoutWindowViewSet(viewsets.ModelViewSet):
    """Manage blackout windows with audit tracking."""

    queryset = (
        BlackoutWindow.objects.select_related("room", "created_by")
        .all()
        .order_by("start_at")
    )
    serializer_class = BlackoutWindowSerializer
    filterset_class = BlackoutFilter
    ordering_fields = ["start_at", "name"]
    permission_classes = [ReadOnlyForAnonymous, AdminSchedulerWrite]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class HolidayViewSet(viewsets.ModelViewSet):
    """Manage holiday ranges."""

    queryset = Holiday.objects.all().order_by("start_date")
    serializer_class = HolidaySerializer
    filterset_class = HolidayFilter
    ordering_fields = ["start_date", "end_date", "name"]
    permission_classes = [ReadOnlyForAnonymous, AdminSchedulerWrite]


class PublicTimetableView(APIView):
    """Read-only timetable aggregated per room."""

    permission_classes = [AllowAny]

    @extend_schema(responses=TimetableResponseSerializer)
    def get(self, request, term_id):  # noqa: ANN001
        term = get_object_or_404(Term, pk=term_id, is_published=True)
        scope = request.query_params.get("scope", "week")
        if scope not in {"day", "week", "month"}:
            raise ValidationError({"scope": "دامنه‌ی زمانی نامعتبر است."})

        date_param = request.query_params.get("date")
        try:
            base_date = (
                dt.date.fromisoformat(date_param) if date_param else term.start_date
            )
        except ValueError as exc:  # pragma: no cover - validated in tests
            raise ValidationError({"date": "فرمت تاریخ معتبر نیست."}) from exc

        local_tz = jalali.get_local_timezone()
        start = dt.datetime.combine(base_date, dt.time.min, tzinfo=local_tz)
        if scope == "day":
            end = start + dt.timedelta(days=1)
        elif scope == "week":
            weekday = start.weekday()
            week_start = start - dt.timedelta(days=weekday)
            start = week_start
            end = start + dt.timedelta(days=7)
        else:  # month
            month_start = start.replace(day=1)
            start = month_start
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            end = next_month

        term_start = dt.datetime.combine(term.start_date, dt.time.min, tzinfo=local_tz)
        term_end = dt.datetime.combine(
            term.end_date,
            dt.time.max,
            tzinfo=local_tz,
        ) + dt.timedelta(seconds=1)

        start = max(start, term_start)
        end = min(end, term_end)

        allocations = (
            ExamAllocation.objects.select_related("exam", "room")
            .filter(exam__term=term)
            .filter(start_at__lt=end, end_at__gt=start)
            .order_by("room__name", "start_at")
        )

        rooms_map: dict[int, dict[str, object]] = {}
        for allocation in allocations:
            room = allocation.room
            room_info = rooms_map.setdefault(
                room.id,
                {
                    "room_id": room.id,
                    "room_name": room.name,
                    "capacity": room.capacity,
                    "allocations": [],
                },
            )
            room_info["allocations"].append(allocation)  # type: ignore[index]

        jalali_label = _format_scope_label(scope, start, end)

        rooms_payload = []
        for info in rooms_map.values():
            allocations_list = info["allocations"]  # type: ignore[index]
            allocations_data = TimetableAllocationSerializer(
                allocations_list,
                many=True,
            ).data
            rooms_payload.append(
                {
                    "room_id": info["room_id"],
                    "room_name": info["room_name"],
                    "capacity": info["capacity"],
                    "allocations": allocations_data,
                }
            )

        response = {
            "term": term.id,
            "label": jalali_label,
            "scope": scope,
            "rooms": rooms_payload,
        }

        serializer = TimetableResponseSerializer(data=response)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


def _format_scope_label(scope: str, start: dt.datetime, end: dt.datetime) -> str:
    """Return a Jalali label describing the selected scope."""

    if scope == "day":
        return jalali.format_jalali(start)

    if scope == "week":
        start_label = jalali.format_jalali(start)
        end_label = jalali.format_jalali(end - dt.timedelta(seconds=1))
        return f"{start_label} تا {end_label}"

    # month
    jalali_start = jalali.to_jalali_datetime(start)
    return f"{jalali_start.strftime('%B %Y')}"
