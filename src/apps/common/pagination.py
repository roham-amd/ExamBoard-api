"""Pagination defaults for the ExamBoard API."""

from __future__ import annotations

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Page-number pagination with configurable page size limits."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
