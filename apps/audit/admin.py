"""
Django Admin configuration for Audit Logs.

Audit logs are read-only in admin — no create, update, or delete.
"""

from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "action",
        "actor_email",
        "target_type",
        "target_id",
        "ip_address",
    ]
    list_filter = ["action", "target_type", "created_at"]
    search_fields = ["actor__email", "target_type", "metadata"]
    readonly_fields = [
        "actor",
        "action",
        "target_type",
        "target_id",
        "metadata",
        "ip_address",
        "created_at",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    def actor_email(self, obj):
        return obj.actor.email if obj.actor else "System"

    actor_email.short_description = "Actor"

    # Prevent any modifications — audit logs are immutable
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False