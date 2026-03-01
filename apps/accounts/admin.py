"""
Django Admin configuration for User model.

This gives you a web UI at /admin/ for managing users directly.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for our User model (email-based, no username)."""

    # List display
    list_display = [
        "email",
        "first_name",
        "last_name",
        "role",
        "is_gi_complete",
        "is_neu_email",
        "is_active",
        "created_at",
    ]
    list_filter = ["role", "is_gi_complete", "is_neu_email", "is_active", "created_at"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]

    # Detail view fieldsets
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        (
            "Platform",
            {
                "fields": ("role", "is_gi_complete", "is_neu_email"),
            },
        ),
        (
            "Django Permissions",
            {
                "fields": ("is_active", "is_staff", "is_superuser"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at", "last_login"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "last_login"]

    # Add user form (when creating via admin)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )