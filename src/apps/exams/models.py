"""Domain models for exam scheduling."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.common.models import TimeStampedModel, UserAuditModel


class Term(TimeStampedModel):
    """Academic term definition."""

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
