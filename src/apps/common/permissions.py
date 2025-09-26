"""Reusable permission helpers for role-based access control."""

from __future__ import annotations

from collections.abc import Iterable

from rest_framework.permissions import BasePermission

ADMIN_GROUP = "Admin"
SCHEDULER_GROUP = "Scheduler"
INSTRUCTOR_GROUP = "Instructor"
STUDENT_GROUP = "Student"


def user_in_groups(
    user, group_names: Iterable[str]
) -> bool:  # noqa: ANN001 - DRF user type
    """Check whether the user belongs to any of the provided groups."""

    if not user or user.is_anonymous:
        return False

    if user.is_superuser:
        return True

    user_groups = set(user.groups.values_list("name", flat=True))
    return any(group in user_groups for group in group_names)


class ReadOnlyForAnonymous(BasePermission):
    """Allow read-only access for unauthenticated users."""

    def has_permission(self, request, view):  # noqa: D401, ANN001
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user and request.user.is_authenticated


class GroupPermission(BasePermission):
    """Allow unsafe methods based on the configured group whitelist."""

    allowed_groups: tuple[str, ...] = ()

    def has_permission(self, request, view):  # noqa: D401, ANN001
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return user_in_groups(request.user, self.allowed_groups)


class AdminOnly(GroupPermission):
    """Restrict write access to admins."""

    allowed_groups = (ADMIN_GROUP,)


class AdminSchedulerWrite(GroupPermission):
    """Allow modifications for admins and schedulers."""

    allowed_groups = (ADMIN_GROUP, SCHEDULER_GROUP)


class AdminSchedulerInstructorWrite(GroupPermission):
    """Allow modifications for admins, schedulers, and instructors."""

    allowed_groups = (ADMIN_GROUP, SCHEDULER_GROUP, INSTRUCTOR_GROUP)
