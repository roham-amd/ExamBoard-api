"""Reusable permission helpers for role-based access control."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

ADMIN_GROUP = "Admin"
SCHEDULER_GROUP = "Scheduler"
INSTRUCTOR_GROUP = "Instructor"
STUDENT_GROUP = "Student"


def user_in_groups(user: Any, group_names: Iterable[str]) -> bool:
    """Check whether the user belongs to any of the provided groups."""

    if not user or getattr(user, "is_anonymous", True):
        return False

    if getattr(user, "is_superuser", False):
        return True

    groups = getattr(user, "groups", None)
    if groups is None:
        return False

    user_groups = set(groups.values_list("name", flat=True))
    return any(group in user_groups for group in group_names)

class ReadOnlyForAnonymous(BasePermission):
    """Allow read-only access for unauthenticated users."""

    def has_permission(self, request: Request, view: APIView) -> bool:  # noqa: D401
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user and request.user.is_authenticated)

class GroupPermission(BasePermission):
    """Allow unsafe methods based on the configured group whitelist."""

    allowed_groups: tuple[str, ...] = ()

    def has_permission(self, request: Request, view: APIView) -> bool:  # noqa: D401
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
