"""Admin registrations for exam scheduling models."""

from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.db import models

from apps.common.jalali import format_jalali, format_jalali_date

from .models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term
from .widgets import JalaliDateWidget, JalaliSplitDateTimeWidget


class JalaliWidgetAdminMixin:
    """Apply Jalali-aware widgets to date and datetime form fields."""

    formfield_overrides = {
        models.DateField: {"widget": JalaliDateWidget},
        models.DateTimeField: {"widget": JalaliSplitDateTimeWidget},
    }


@admin.register(Term)
class TermAdmin(JalaliWidgetAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "start_date",
        "end_date",
        "is_published",
        "is_archived",
        "start_date_jalali",
        "end_date_jalali",
    )
    list_filter = (
        "is_published",
        "is_archived",
        ("start_date", DateFieldListFilter),
        ("end_date", DateFieldListFilter),
    )
    search_fields = ("name", "code")
    ordering = ("-start_date", "code")
    readonly_fields = ("start_date_jalali", "end_date_jalali")

    @admin.display(description="شروع (جلالی)")
    def start_date_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali_date(obj.start_date)

    @admin.display(description="پایان (جلالی)")
    def end_date_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali_date(obj.end_date)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Exam)
class ExamAdmin(JalaliWidgetAdminMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "course_code",
        "term",
        "owner",
        "expected_students",
        "duration_minutes",
    )
    list_filter = ("term", ("created_at", DateFieldListFilter))
    search_fields = ("title", "course_code", "owner__username", "term__code")
    autocomplete_fields = ("owner", "term")


@admin.register(ExamAllocation)
class ExamAllocationAdmin(JalaliWidgetAdminMixin, admin.ModelAdmin):
    list_display = (
        "exam",
        "room",
        "start_at",
        "end_at",
        "allocated_seats",
        "start_at_jalali",
        "end_at_jalali",
    )
    list_filter = (
        "room",
        "exam__term",
        ("start_at", DateFieldListFilter),
    )
    autocomplete_fields = ("exam", "room")
    date_hierarchy = "start_at"
    search_fields = (
        "exam__title",
        "exam__course_code",
        "room__name",
    )
    readonly_fields = ("start_at_jalali", "end_at_jalali")

    @admin.display(description="شروع (جلالی)")
    def start_at_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali(obj.start_at)

    @admin.display(description="پایان (جلالی)")
    def end_at_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali(obj.end_at)


@admin.register(BlackoutWindow)
class BlackoutWindowAdmin(JalaliWidgetAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "start_at",
        "end_at",
        "start_at_jalali",
        "end_at_jalali",
        "room",
        "created_by",
    )
    list_filter = ("room", ("start_at", DateFieldListFilter))
    autocomplete_fields = ("room", "created_by", "updated_by")
    date_hierarchy = "start_at"
    search_fields = ("name", "room__name")
    readonly_fields = ("start_at_jalali", "end_at_jalali")

    @admin.display(description="شروع (جلالی)")
    def start_at_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali(obj.start_at)

    @admin.display(description="پایان (جلالی)")
    def end_at_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali(obj.end_at)


@admin.register(Holiday)
class HolidayAdmin(JalaliWidgetAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "start_date",
        "end_date",
        "start_date_jalali",
        "end_date_jalali",
    )
    list_filter = (
        ("start_date", DateFieldListFilter),
        ("end_date", DateFieldListFilter),
    )
    date_hierarchy = "start_date"
    search_fields = ("name",)
    readonly_fields = ("start_date_jalali", "end_date_jalali")

    @admin.display(description="شروع (جلالی)")
    def start_date_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali_date(obj.start_date)

    @admin.display(description="پایان (جلالی)")
    def end_date_jalali(self, obj):  # noqa: ANN001 - admin signature
        return format_jalali_date(obj.end_date)
