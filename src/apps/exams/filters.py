"""FilterSet definitions for exam scheduling endpoints."""

from __future__ import annotations

import django_filters

from .models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


class TermFilter(django_filters.FilterSet):
    """Support filtering terms by publication status and code."""

    class Meta:
        model = Term
        fields = {
            "code": ["exact", "icontains"],
            "is_published": ["exact"],
            "is_archived": ["exact"],
        }


class RoomFilter(django_filters.FilterSet):
    """Filtering options for rooms."""

    class Meta:
        model = Room
        fields = {
            "name": ["exact", "icontains"],
            "capacity": ["exact", "gte", "lte"],
        }


class ExamFilter(django_filters.FilterSet):
    """Filter exams by ownership, course code, and term."""

    min_expected = django_filters.NumberFilter(
        field_name="expected_students", lookup_expr="gte"
    )
    max_expected = django_filters.NumberFilter(
        field_name="expected_students", lookup_expr="lte"
    )

    class Meta:
        model = Exam
        fields = {
            "term": ["exact"],
            "owner": ["exact"],
            "course_code": ["exact", "icontains"],
            "title": ["icontains"],
        }


class ExamAllocationFilter(django_filters.FilterSet):
    """Filter allocations by exam, room, and time range."""

    term = django_filters.NumberFilter(field_name="exam__term_id")
    starts_after = django_filters.DateTimeFilter(
        field_name="start_at", lookup_expr="gte"
    )
    starts_before = django_filters.DateTimeFilter(
        field_name="start_at", lookup_expr="lte"
    )
    in_range = django_filters.IsoDateTimeFromToRangeFilter(method="filter_in_range")

    class Meta:
        model = ExamAllocation
        fields = {
            "exam": ["exact"],
            "room": ["exact"],
        }

    def filter_in_range(self, queryset, name, value):  # noqa: ANN001
        if not value or not all([value.start, value.stop]):
            return queryset
        start, end = value.start, value.stop
        return queryset.filter(start_at__lt=end, end_at__gt=start)


class BlackoutFilter(django_filters.FilterSet):
    """Filter blackout windows by room and overlap."""

    overlaps = django_filters.IsoDateTimeFromToRangeFilter(method="filter_overlaps")

    class Meta:
        model = BlackoutWindow
        fields = {
            "room": ["exact", "isnull"],
        }

    def filter_overlaps(self, queryset, name, value):  # noqa: ANN001
        if not value or not all([value.start, value.stop]):
            return queryset
        return queryset.filter(start_at__lt=value.stop, end_at__gt=value.start)


class HolidayFilter(django_filters.FilterSet):
    """Filter holidays by inclusive date range."""

    overlaps = django_filters.DateFromToRangeFilter(method="filter_overlaps")

    class Meta:
        model = Holiday
        fields = {
            "start_date": ["exact", "gte", "lte"],
            "end_date": ["exact", "gte", "lte"],
        }

    def filter_overlaps(self, queryset, name, value):  # noqa: ANN001
        if not value or not all([value.start, value.stop]):
            return queryset
        return queryset.filter(start_date__lte=value.stop, end_date__gte=value.start)
