"""Admin registrations for exam scheduling models."""

from django.contrib import admin

from .models import BlackoutWindow, Exam, ExamAllocation, Holiday, Room, Term


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "start_date",
        "end_date",
        "is_published",
        "is_archived",
    )
    list_filter = ("is_published", "is_archived")
    search_fields = ("name", "code")
    ordering = ("-start_date", "code")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course_code",
        "term",
        "owner",
        "expected_students",
        "duration_minutes",
    )
    list_filter = ("term",)
    search_fields = ("title", "course_code", "owner__username")
    autocomplete_fields = ("owner", "term")


@admin.register(ExamAllocation)
class ExamAllocationAdmin(admin.ModelAdmin):
    list_display = ("exam", "room", "start_at", "end_at", "allocated_seats")
    list_filter = ("room", "exam__term")
    autocomplete_fields = ("exam", "room")
    date_hierarchy = "start_at"


@admin.register(BlackoutWindow)
class BlackoutWindowAdmin(admin.ModelAdmin):
    list_display = ("name", "start_at", "end_at", "room", "created_by")
    list_filter = ("room",)
    autocomplete_fields = ("room", "created_by", "updated_by")
    date_hierarchy = "start_at"


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    date_hierarchy = "start_date"
    search_fields = ("name",)
