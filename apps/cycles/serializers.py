"""
Cycle serializers — input validation and output formatting.
"""

from rest_framework import serializers

from apps.cycles.models import ApplicationCycle


class CreateCycleSerializer(serializers.Serializer):
    """Input DTO for creating a new application cycle."""

    name = serializers.CharField(
        max_length=100,
        help_text='Human-readable name, e.g. "Fall 2026"',
    )
    description = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        help_text="Optional notes for this cycle.",
    )

    def validate_name(self, value):
        """Ensure cycle name is unique."""
        if ApplicationCycle.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError(
                "A cycle with this name already exists."
            )
        return value.strip()


class UpdateCycleTogglesSerializer(serializers.Serializer):
    """
    Input DTO for updating cycle toggles.

    All fields are optional — only provided fields are updated.
    This allows the admin to flip one toggle without touching the other.

    Uses NullBooleanField so that omitted fields come through as None,
    which the service layer interprets as "don't change this toggle".
    """

    launch_open = serializers.BooleanField(required=False, allow_null=True, default=None)
    innovation_open = serializers.BooleanField(required=False, allow_null=True, default=None)

    def validate(self, data):
        # Check if at least one toggle was actually provided (not None)
        has_launch = data.get("launch_open") is not None
        has_innovation = data.get("innovation_open") is not None
        if not has_launch and not has_innovation:
            raise serializers.ValidationError(
                "At least one toggle must be provided (launch_open or innovation_open)."
            )
        return data


class CycleDetailSerializer(serializers.ModelSerializer):
    """Output DTO for cycle details."""

    class Meta:
        model = ApplicationCycle
        fields = [
            "id",
            "name",
            "is_active",
            "launch_open",
            "innovation_open",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CycleListSerializer(serializers.ModelSerializer):
    """Lightweight output DTO for cycle listing."""

    class Meta:
        model = ApplicationCycle
        fields = [
            "id",
            "name",
            "is_active",
            "launch_open",
            "innovation_open",
            "created_at",
        ]
        read_only_fields = fields


class CycleStatsSerializer(serializers.Serializer):
    """Output DTO for cycle statistics dashboard."""

    cycle_id = serializers.IntegerField()
    cycle_name = serializers.CharField()
    is_active = serializers.BooleanField()
    launch_open = serializers.BooleanField()
    innovation_open = serializers.BooleanField()
    total_users = serializers.IntegerField()
    gi_completed = serializers.IntegerField()
    gi_pending = serializers.IntegerField()
    # Populated in later phases
    launch_apps = serializers.IntegerField(default=0)
    launch_assigned = serializers.IntegerField(default=0)
    innovation_proposals = serializers.IntegerField(default=0)
    innovation_assigned = serializers.IntegerField(default=0)
    unassigned_users = serializers.IntegerField(default=0)