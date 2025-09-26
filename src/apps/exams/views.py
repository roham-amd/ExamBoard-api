"""Viewsets for the exam scheduling API."""

from __future__ import annotations

import datetime as dt

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import jalali
from apps.common.pagination import StandardResultsSetPagination
from apps.common.permissions import (
    AdminOnly,
    AdminSchedulerInstructorWrite,
    AdminSchedulerWrite,
    ReadOnlyForAnonymous,
    user_in_groups,
)
from apps.common.serializers import JalaliDateField, JalaliDateTimeField

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
    RoomCapacityHeatmapResponseSerializer,
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
        term.publish()
        serializer = self.get_serializer(term)
        return Response(serializer.data)


class RoomViewSet(viewsets.ModelViewSet):
    """Manage rooms with read-only access for anonymous users."""

    queryset = Room.objects.all().order_by("name")
    serializer_class = RoomSerializer
    filterset_class = RoomFilter
    ordering_fields = ["name", "capacity"]
    permission_classes = [ReadOnlyForAnonymous, AdminSchedulerWrite]

    @action(
        detail=False,
        methods=["get"],
        url_path="capacity-heatmap",
        permission_classes=[ReadOnlyForAnonymous],
    )
    @extend_schema(
        responses=RoomCapacityHeatmapResponseSerializer,
        parameters=[
            OpenApiParameter(
                name="term",
                type=OpenApiTypes.INT,
                required=True,
                location=OpenApiParameter.QUERY,
                description="شناسهٔ ترم برای محاسبهٔ ظرفیت.",
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                required=False,
                location=OpenApiParameter.QUERY,
                description="تاریخ شروع بازهٔ مورد نظر (ISO).",
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                required=False,
                location=OpenApiParameter.QUERY,
                description="تاریخ پایان بازهٔ مورد نظر (ISO).",
            ),
            OpenApiParameter(
                name="room",
                type=OpenApiTypes.INT,
                required=False,
                location=OpenApiParameter.QUERY,
                description="می‌توان یک یا چند شناسهٔ اتاق را برای فیلتر کردن ارسال کرد.",
            ),
        ],
    )
    def capacity_heatmap(self, request):  # noqa: ANN001
        term_id = request.query_params.get("term")
        if not term_id:
            raise ValidationError({"term": "انتخاب ترم الزامی است."})

        term = get_object_or_404(Term, pk=term_id)

        try:
            start_param = request.query_params.get("start_date")
            end_param = request.query_params.get("end_date")
            start_date = (
                dt.date.fromisoformat(start_param) if start_param else term.start_date
            )
            end_date = dt.date.fromisoformat(end_param) if end_param else term.end_date
        except ValueError as exc:
            raise ValidationError({"date": "فرمت تاریخ معتبر نیست."}) from exc

        room_params = request.query_params.getlist("room")
        try:
            room_ids = [int(value) for value in room_params]
        except ValueError as exc:
            raise ValidationError({"room": "شناسهٔ اتاق باید عددی باشد."}) from exc

        start_date = max(start_date, term.start_date)
        end_date = min(end_date, term.end_date)

        if start_date > end_date:
            raise ValidationError({"start_date": "محدودهٔ تاریخ باید داخل ترم باشد."})

        rooms_qs = Room.objects.all().order_by("name")
        if room_ids:
            rooms_qs = rooms_qs.filter(id__in=room_ids)

        rooms = list(rooms_qs)
        if room_ids and len({room.id for room in rooms}) != len(set(room_ids)):
            raise ValidationError({"room": "برخی شناسه‌های اتاق موجود نیستند."})

        if not rooms:
            response_payload = {
                "term": TermSerializer(term).data,
                "start_date": JalaliDateField().to_representation(start_date),
                "end_date": JalaliDateField().to_representation(end_date),
                "rooms": [],
            }
            return Response(response_payload)

        local_tz = jalali.get_local_timezone()
        aware_start = jalali.ensure_aware(dt.datetime.combine(start_date, dt.time.min))
        aware_end = jalali.ensure_aware(
            dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time.min)
        )

        allocations = (
            ExamAllocation.objects.select_related("room")
            .filter(exam__term=term, room__in=rooms)
            .filter(start_at__lt=aware_end.astimezone(dt.UTC))
            .filter(end_at__gt=aware_start.astimezone(dt.UTC))
            .order_by("room__name", "start_at")
        )

        all_dates = [
            start_date + dt.timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        ]

        events_by_room: dict[int, dict[dt.date, list[tuple[dt.datetime, int]]]] = {
            room.id: {day: [] for day in all_dates} for room in rooms
        }
        totals_by_room: dict[int, dict[dt.date, int]] = {
            room.id: {day: 0 for day in all_dates} for room in rooms
        }
        counts_by_room: dict[int, dict[dt.date, int]] = {
            room.id: {day: 0 for day in all_dates} for room in rooms
        }

        def sort_key(event: tuple[dt.datetime, int]) -> tuple[dt.datetime, int]:
            timestamp, delta = event
            return (timestamp, 0 if delta < 0 else 1)

        for allocation in allocations:
            room_id = allocation.room_id
            local_start = timezone.localtime(allocation.start_at, local_tz)
            local_end = timezone.localtime(allocation.end_at, local_tz)
            inclusive_end = local_end - dt.timedelta(microseconds=1)

            current_day = local_start.date()
            final_day = inclusive_end.date()

            while current_day <= final_day:
                if current_day < start_date or current_day > end_date:
                    current_day += dt.timedelta(days=1)
                    continue

                day_start = dt.datetime.combine(
                    current_day, dt.time.min, tzinfo=local_tz
                )
                day_end = day_start + dt.timedelta(days=1)

                interval_start = max(local_start, day_start)
                interval_end = min(local_end, day_end)

                if interval_start < interval_end:
                    events_by_room[room_id][current_day].append(
                        (interval_start, allocation.allocated_seats)
                    )
                    events_by_room[room_id][current_day].append(
                        (interval_end, -allocation.allocated_seats)
                    )
                    totals_by_room[room_id][current_day] += allocation.allocated_seats
                    counts_by_room[room_id][current_day] += 1

                current_day += dt.timedelta(days=1)

        date_field = JalaliDateField()
        rooms_payload = []
        for room in rooms:
            days_payload = []
            for day in all_dates:
                events = sorted(events_by_room[room.id][day], key=sort_key)
                current_load = 0
                peak_load = 0
                for _, delta in events:
                    current_load += delta
                    if current_load > peak_load:
                        peak_load = current_load

                capacity = room.capacity or 1
                utilisation = peak_load / capacity if capacity else 0.0

                days_payload.append(
                    {
                        "date": date_field.to_representation(day),
                        "peak_allocated_seats": peak_load,
                        "total_allocated_seats": totals_by_room[room.id][day],
                        "allocation_count": counts_by_room[room.id][day],
                        "utilisation": round(utilisation, 4),
                    }
                )

            rooms_payload.append(
                {
                    "id": room.id,
                    "name": room.name,
                    "capacity": room.capacity,
                    "days": days_payload,
                }
            )

        response_payload = {
            "term": TermSerializer(term).data,
            "start_date": date_field.to_representation(start_date),
            "end_date": date_field.to_representation(end_date),
            "rooms": rooms_payload,
        }

        return Response(response_payload)


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
    pagination_class = StandardResultsSetPagination

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

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rooms_payload, request, view=self)
        paginated_rooms = page if page is not None else rooms_payload

        jalali_field = JalaliDateTimeField()
        requested_range = {
            "scope": scope,
            "label": jalali_label,
            "start": jalali_field.to_representation(start),
            "end": jalali_field.to_representation(end),
        }

        response = {
            "term": TermSerializer(term).data,
            "requested_range": requested_range,
            "rooms": paginated_rooms,
        }

        if page is not None:
            response["pagination"] = {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            }

        return Response(response)


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
