"""Domain models for exam scheduling."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.common.models import TimeStampedModel, UserAuditModel


class Term(TimeStampedModel):
    """Academic term definition."""

    LOCKED_FIELDS: tuple[str, ...] = ("code", "start_date", "end_date")

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ("-start_date", "code")
        constraints = [
            models.CheckConstraint(
                check=Q(start_date__lte=F("end_date")),
                name="term_start_before_or_equal_end",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        super().clean()

        if not self.pk:
            return

        try:
            original = Term.objects.get(pk=self.pk)
        except Term.DoesNotExist:  # pragma: no cover - safety guard
            return

        if not original.is_published:
            return

        locked_errors = {}
        for field_name in self.LOCKED_FIELDS:
            if getattr(self, field_name) != getattr(original, field_name):
                locked_errors[field_name] = "این فیلد پس از انتشار قابل تغییر نیست."

        if locked_errors:
            raise ValidationError(locked_errors)

    def publish(self, *, commit: bool = True) -> Term:
        """Mark the term as published and lock schema-critical fields."""

        if self.is_published:
            return self

        self.is_published = True

        if commit:
            self.save(update_fields=["is_published", "updated_at"])

        return self


class Room(TimeStampedModel):
    """Physical exam room."""

    name = models.CharField(max_length=128, unique=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    features = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"{self.name} (cap. {self.capacity})"


class Exam(TimeStampedModel):
    """Exam instance owned by a staff member."""

    title = models.CharField(max_length=255)
    course_code = models.CharField(max_length=64)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="exams",
    )
    expected_students = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    duration_minutes = models.PositiveIntegerField(
        default=60, validators=[MinValueValidator(1)]
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="exams",
    )

    class Meta:
        ordering = ("title",)
        constraints = [
            models.UniqueConstraint(
                fields=("course_code", "term"),
                name="unique_course_code_per_term",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"{self.title} ({self.course_code})"


class ExamAllocation(TimeStampedModel):
    """Allocation of an exam to a room slot."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    allocated_seats = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(start_at__lt=F("end_at")),
                name="exam_allocation_start_before_end",
            )
        ]
        ordering = ("start_at",)

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"{self.exam} @ {self.room}"

    def clean(self) -> None:
        super().clean()

        if not all([self.exam_id, self.room_id, self.start_at, self.end_at]):
            return

        self._validate_term_window()
        self._validate_blackouts()
        self._validate_holidays()
        self._validate_capacity()

    def save(self, *args, **kwargs):  # type: ignore[override]
        """Persist the allocation while guarding against race conditions."""

        with transaction.atomic():
            if self.room_id and self.start_at and self.end_at:
                overlap_qs = (
                    ExamAllocation.objects.select_for_update()
                    .filter(room_id=self.room_id)
                    .filter(start_at__lt=self.end_at, end_at__gt=self.start_at)
                )
                if self.pk:
                    overlap_qs = overlap_qs.exclude(pk=self.pk)
                self._locked_overlaps = list(overlap_qs)
            try:
                self.full_clean()
                return super().save(*args, **kwargs)
            finally:
                if hasattr(self, "_locked_overlaps"):
                    delattr(self, "_locked_overlaps")

    # Validation helpers -------------------------------------------------

    def _validate_term_window(self) -> None:
        term = self.exam.term
        local_start = timezone.localtime(self.start_at)
        local_end = timezone.localtime(self.end_at)
        inclusive_end = local_end - dt.timedelta(microseconds=1)

        if local_start.date() < term.start_date or inclusive_end.date() > term.end_date:
            raise ValidationError({"start_at": "زمان تخصیص باید داخل محدوده ترم باشد."})

    def _validate_blackouts(self) -> None:
        blackout_q = Q(room=self.room) | Q(room__isnull=True)
        overlapping_blackouts = BlackoutWindow.objects.filter(blackout_q).filter(
            start_at__lt=self.end_at, end_at__gt=self.start_at
        )
        if overlapping_blackouts.exists():
            raise ValidationError(
                {"start_at": "این بازه زمانی به علت محدودیت برنامه‌ریزی امکان‌پذیر نیست."}
            )

    def _validate_holidays(self) -> None:
        local_start = timezone.localtime(self.start_at)
        local_end = timezone.localtime(self.end_at)
        inclusive_end = local_end - dt.timedelta(microseconds=1)
        start_date = local_start.date()
        end_date = inclusive_end.date()

        holiday_exists = Holiday.objects.filter(
            start_date__lte=end_date, end_date__gte=start_date
        ).exists()
        if holiday_exists:
            raise ValidationError({"start_at": "این بازه در تقویم تعطیلات قرار دارد."})

    def _validate_capacity(self) -> None:
        room_capacity = self.room.capacity
        overlapping_allocations = self._get_overlapping_allocations()

        events: list[tuple[dt.datetime, int]] = []
        for allocation in overlapping_allocations:
            events.append((allocation.start_at, allocation.allocated_seats))
            events.append((allocation.end_at, -allocation.allocated_seats))

        events.append((self.start_at, self.allocated_seats))
        events.append((self.end_at, -self.allocated_seats))

        def sort_key(event: tuple[dt.datetime, int]) -> tuple[dt.datetime, int]:
            timestamp, delta = event
            # Apply departures before arrivals when timestamps match.
            return (timestamp, 0 if delta < 0 else 1)

        current_load = 0
        for _timestamp, delta in sorted(events, key=sort_key):
            current_load += delta
            if current_load > room_capacity:
                raise ValidationError(
                    {
                        "allocated_seats": "ظرفیت اتاق در این بازه زمانی تکمیل است.",
                    }
                )

    def _get_overlapping_allocations(self) -> Iterable[ExamAllocation]:
        if hasattr(self, "_locked_overlaps"):
            return self._locked_overlaps

        qs = ExamAllocation.objects.filter(room=self.room).filter(
            start_at__lt=self.end_at, end_at__gt=self.start_at
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs


class BlackoutWindow(TimeStampedModel, UserAuditModel):
    """Periods where scheduling is not permitted."""

    name = models.CharField(max_length=255)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="blackout_windows",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(start_at__lt=F("end_at")),
                name="blackoutwindow_start_before_end",
            )
        ]
        ordering = ("start_at", "name")

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        scope = self.room.name if self.room else "All rooms"
        return f"{self.name} ({scope})"


class Holiday(TimeStampedModel):
    """All-day ranges where exams are not scheduled."""

    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ("start_date", "name")
        constraints = [
            models.CheckConstraint(
                check=Q(start_date__lte=F("end_date")),
                name="holiday_start_before_or_equal_end",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"{self.name} ({self.start_date} - {self.end_date})"
