"""Serializers for exam scheduling APIs."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.common.serializers import JalaliDateTimeField

from .models import ExamAllocation


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
