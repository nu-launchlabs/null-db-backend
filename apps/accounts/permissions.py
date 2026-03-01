"""
Role-based permission classes.

Usage in views:
    permission_classes = [IsAuthenticated, IsAdmin]

These are composable - stack them using lists or use the Or/And combos below.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsAdmin(BasePermission):
    """Allows access only to ADMIN users."""

    message = "Admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsOpsChair(BasePermission):
    """Allows access only to OPS_CHAIR users."""

    message = "Operations Chair access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.OPS_CHAIR
        )


class IsAdminOrOpsChair(BasePermission):
    """Allows access to ADMIN or OPS_CHAIR users."""

    message = "Admin or Operations Chair access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in [User.Role.ADMIN, User.Role.OPS_CHAIR]
        )


class IsLaunchTeam(BasePermission):
    """Allows access only to LAUNCH_TEAM users."""

    message = "Launch Team access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.LAUNCH_TEAM
        )


class IsStudentUser(BasePermission):
    """Allows access only to USER (student) role."""

    message = "Student access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.USER
        )


class IsGIComplete(BasePermission):
    """
    Allows access only if user has completed General Interest form.
    Used as a gate for Launch/Innovation applications.
    """

    message = "Complete the General Interest form first."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_gi_complete
        )


class IsSelf(BasePermission):
    """
    Object-level permission: user can only access their own resource.
    Used for profile endpoints.
    """

    message = "You can only access your own data."

    def has_object_permission(self, request, view, obj):
        return obj == request.user or obj.user == request.user