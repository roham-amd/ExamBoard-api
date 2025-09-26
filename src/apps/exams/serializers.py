"""Serializers for exam scheduling APIs."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.common.serializers import JalaliDateField, JalaliDateTimeField

from .models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


class TermSerializer(serializers.ModelSerializer):
    """Expose term metadata with dual-calendar fields."""

    start_date = JalaliDateField()
    end_date = JalaliDateField()

    class Meta:
        model = Term
        fields = [
            "id",
            "name",
            "code",
            "start_date",
            "end_date",
            "is_published",
            "is_archived",
        ]
        read_only_fields = ["id"]


class RoomSerializer(serializers.ModelSerializer):
    """Serialize room details."""

    class Meta:
        model = Room
        fields = ["id", "name", "capacity", "features"]
        read_only_fields = ["id"]


class ExamSerializer(serializers.ModelSerializer):
    """Serialize exam definitions."""

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "course_code",
            "owner",
            "expected_students",
            "duration_minutes",
            "term",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {"owner": {"required": False}}


class ExamAllocationSerializer(serializers.ModelSerializer):
    """Serialise exam allocation details with Jalali timestamps."""

    start_at = JalaliDateTimeField()
    end_at = JalaliDateTimeField()

    class Meta:
        model = ExamAllocation
        fields = [
            "id",
            "exam",
            "room",
            "start_at",
            "end_at",
            "allocated_seats",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        instance = self.instance
        if instance is not None:
            for attr, value in attrs.items():
                setattr(instance, attr, value)
        else:
            instance = ExamAllocation(**attrs)

        try:
            instance.clean()
        except ValidationError as exc:  # pragma: no cover - DRF handles raising
            detail = exc.message_dict or {"non_field_errors": exc.messages}
            raise serializers.ValidationError(detail) from exc

        return attrs


class BlackoutWindowSerializer(serializers.ModelSerializer):
    """Expose blackout windows with Jalali timestamps."""

    start_at = JalaliDateTimeField()
    end_at = JalaliDateTimeField()

    class Meta:
        model = BlackoutWindow
        fields = ["id", "name", "start_at", "end_at", "room", "created_by"]
        read_only_fields = ["id", "created_by"]


class HolidaySerializer(serializers.ModelSerializer):
    """Serialize holiday ranges."""

    start_date = JalaliDateField()
    end_date = JalaliDateField()

    class Meta:
        model = Holiday
        fields = ["id", "name", "start_date", "end_date"]
        read_only_fields = ["id"]


class TimetableAllocationSerializer(serializers.ModelSerializer):
    """Public timetable representation of allocations."""

    start_at = JalaliDateTimeField(read_only=True)
    end_at = JalaliDateTimeField(read_only=True)
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    course_code = serializers.CharField(source="exam.course_code", read_only=True)

    class Meta:
        model = ExamAllocation
        fields = [
            "id",
            "exam_title",
            "course_code",
            "start_at",
            "end_at",
            "allocated_seats",
        ]


class TimetableRoomSerializer(serializers.Serializer):
    """Aggregate allocations for a single room in the public timetable."""

    room_id = serializers.IntegerField()
    room_name = serializers.CharField()
    capacity = serializers.IntegerField()
    allocations = TimetableAllocationSerializer(many=True)


class TimetableResponseSerializer(serializers.Serializer):
    """Serializer used for documenting the public timetable response."""

    term = serializers.IntegerField()
    label = serializers.CharField()
    scope = serializers.CharField()
    rooms = TimetableRoomSerializer(many=True)

