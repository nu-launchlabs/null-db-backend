"""
Django Admin configuration for Application Cycles.
"""

from django.contrib import admin

from apps.cycles.models import ApplicationCycle


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
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )