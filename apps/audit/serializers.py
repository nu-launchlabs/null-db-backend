"""
Audit serializers — output formatting for audit log entries.
"""

from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Output DTO for audit log entries."""

    actor_email = serializers.SerializerMethodField()
    action_display = serializers.CharField(
        source="get_action_display", read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "action",
            "action_display",
            "target_type",
            "target_id",
            "metadata",
            "ip_address",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else "System"