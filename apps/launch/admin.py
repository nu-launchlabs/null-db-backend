"""
Django Admin configuration for Launch Track models.
"""

from django.contrib import admin

from apps.launch.models import LaunchApplication, LaunchCandidate, LaunchProject


@admin.register(LaunchProject)
class LaunchProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "team", "cycle", "max_members", "created_at"]
    list_filter = ["cycle"]
    search_fields = ["title", "team__email", "team__first_name", "team__last_name"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["team", "cycle"]


@admin.register(LaunchApplication)
class LaunchApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "project",
        "cycle",
        "status",
        "created_at",
    ]
    list_filter = ["status", "cycle"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "project__title",
    ]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["user", "project", "cycle"]


@admin.register(LaunchCandidate)
class LaunchCandidateAdmin(admin.ModelAdmin):
    list_display = [
        "application",
        "project",
        "status",
        "selected_at",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = [
        "application__user__email",
        "project__title",
    ]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["application", "project"]