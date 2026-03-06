"""
Audit Log model — immutable action trail for the entire platform.

Every significant action creates one row here.
Rows are NEVER updated or deleted.
"""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit trail entry.

    Records who did what, to which resource, when, and from where.
    The metadata JSON field stores action-specific details.
    """

    class Action(models.TextChoices):
        """All auditable actions across the platform."""

        # Accounts (Phase 1 + 2)
        USER_REGISTERED = "USER_REGISTERED", "User Registered"
        LAUNCH_TEAM_CREATED = "LAUNCH_TEAM_CREATED", "Launch Team Created"
        GI_SUBMITTED = "GI_SUBMITTED", "General Interest Submitted"
        GI_UPDATED = "GI_UPDATED", "General Interest Updated"
        ROLE_CHANGED = "ROLE_CHANGED", "Role Changed"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password Changed"

        # Cycles (Phase 2)
        CYCLE_CREATED = "CYCLE_CREATED", "Cycle Created"
        CYCLE_TOGGLES_UPDATED = "CYCLE_TOGGLES_UPDATED", "Cycle Toggles Updated"
        CYCLE_CLOSED = "CYCLE_CLOSED", "Cycle Closed"

        # Launch (Phase 3)
        LAUNCH_PROJECT_CREATED = "LAUNCH_PROJECT_CREATED", "Launch Project Created"
        LAUNCH_PROJECT_DELETED = "LAUNCH_PROJECT_DELETED", "Launch Project Deleted"
        LAUNCH_APP_SUBMITTED = "LAUNCH_APP_SUBMITTED", "Launch Application Submitted"
        CANDIDATE_SENT_TO_TEAM = "CANDIDATE_SENT_TO_TEAM", "Candidate Sent to Team"
        CANDIDATE_SELECTED = "CANDIDATE_SELECTED", "Candidate Selected"
        LAUNCH_SELECTION_CONFIRMED = (
            "LAUNCH_SELECTION_CONFIRMED",
            "Launch Selection Confirmed",
        )

        # Innovation (Phase 4)
        PROPOSAL_SUBMITTED = "PROPOSAL_SUBMITTED", "Proposal Submitted"
        PROPOSAL_APPROVED = "PROPOSAL_APPROVED", "Proposal Approved"
        PROPOSAL_REJECTED = "PROPOSAL_REJECTED", "Proposal Rejected"
        INNOVATION_PROJECT_DELETED = (
            "INNOVATION_PROJECT_DELETED",
            "Innovation Project Deleted",
        )
        PREFERENCES_SUBMITTED = "PREFERENCES_SUBMITTED", "Preferences Submitted"
        INNOVATION_ASSIGNED = "INNOVATION_ASSIGNED", "Innovation Assigned"

        # Admin (Phase 5)
        ASSIGNMENT_REMOVED = "ASSIGNMENT_REMOVED", "Assignment Removed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="The user who performed the action.",
    )
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
    )
    target_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text='The model type affected, e.g. "User", "ApplicationCycle".',
    )
    target_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="The primary key of the affected record.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Action-specific details (flexible key-value).",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request that triggered this action.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        actor_email = self.actor.email if self.actor else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor_email} → {self.action}"