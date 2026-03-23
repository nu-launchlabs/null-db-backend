"""
Launch-specific permission classes.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsLaunchTeamForProject(BasePermission):
    """
    Object-level permission: Launch Team member can only access
    candidates/projects that belong to them.

    Note: This is primarily enforced in the service layer via
    project.team_id checks. This permission class is for view-level
    documentation and consistency with the pattern.
    """

    message = "You can only access your own project's candidates."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.LAUNCH_TEAM
        )