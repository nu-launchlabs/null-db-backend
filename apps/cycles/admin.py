"""
Django Admin configuration for Application Cycles and Assignments.
"""

from django.contrib import admin

from apps.cycles.models import ApplicationCycle, Assignment


@admin.register(ApplicationCycle)
class ApplicationCycleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "is_active",
        "launch_open",
        "innovation_open",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_active", "launch_open", "innovation_open"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("name", "description", "is_active")}),
        ("Track Toggles", {"fields": ("launch_open", "innovation_open")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "cycle",
        "track",
        "launch_project",
        "innovation_project_id_placeholder",
        "assigned_by",
        "assigned_at",
    ]
    list_filter = ["track", "cycle"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = ["assigned_at", "created_at", "updated_at"]
    raw_id_fields = [
        "user",
        "cycle",
        "launch_project",
        "assigned_by",
    ]