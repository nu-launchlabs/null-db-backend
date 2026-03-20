"""
Application Cycle model — semester container with independent track toggles.

No linear state machine. Admin controls two independent toggles:
    - launch_open: students can apply to Launch projects
    - innovation_open: students can propose projects + rank preferences

Admin/Ops can assign students, manage projects, and review applications
at any time while the cycle is active — regardless of toggle state.

Only one cycle can be active at a time (enforced in service layer).
"""

from django.conf import settings
from django.db import models

from utils.mixins import TimestampMixin


class ApplicationCycle(TimestampMixin, models.Model):
    """
    Represents one semester's application cycle (e.g. "Fall 2026").

    The two toggles (launch_open, innovation_open) are independent.
    They can be on/off in any combination at any time.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Human-readable name, e.g. "Fall 2026"',
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Only one cycle can be active at a time.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional description or notes for this cycle.",
    )

    # Independent Track Toggles
    launch_open = models.BooleanField(
        default=False,
        help_text=(
            "When True, students can apply to Launch projects and "
            "Launch Teams can review/select candidates."
        ),
    )
    innovation_open = models.BooleanField(
        default=False,
        help_text=(
            "When True, students can submit Innovation proposals "
            "and rank Innovation project preferences."
        ),
    )

    class Meta:
        db_table = "application_cycles"
        ordering = ["-created_at"]
        verbose_name = "Application Cycle"
        verbose_name_plural = "Application Cycles"

    def __str__(self):
        status_parts = []
        if self.launch_open:
            status_parts.append("Launch Open")
        if self.innovation_open:
            status_parts.append("Innovation Open")
        if not status_parts:
            status_parts.append("All Closed")

        active_label = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({active_label} — {', '.join(status_parts)})"


class Assignment(TimestampMixin, models.Model):
    """
    The single source of truth for student-project assignments.

    Core constraint: UNIQUE(user, cycle) = one project per student per semester.

    Phase 3: Only Launch assignments are supported via FK.
    innovation_project_id_placeholder stores the InnovationProject ID as a
    plain integer. In Phase 4, this becomes a proper ForeignKey and the
    CHECK constraint is added to enforce exactly-one-project.
    """

    class Track(models.TextChoices):
        LAUNCH = "LAUNCH", "Launch"
        INNOVATION = "INNOVATION", "Innovation"

    # Who is assigned
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    # Which cycle
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    # Which track
    track = models.CharField(
        max_length=20,
        choices=Track.choices,
        help_text="LAUNCH or INNOVATION",
    )

    # Launch FK (active now)
    launch_project = models.ForeignKey(
        "launch.LaunchProject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )

    # Innovation placeholder (becomes FK in Phase 4)
    innovation_project_id_placeholder = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Placeholder for InnovationProject ID. Becomes FK in Phase 4.",
    )

    # Who made the assignment
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments_made",
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assignments"
        ordering = ["-assigned_at"]
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "cycle"],
                name="one_assignment_per_user_per_cycle",
            ),
            # CHECK constraint for exactly-one-project will be added in Phase 4
            # when innovation_project becomes a proper FK.
        ]

    def __str__(self):
        project = self.launch_project or f"Innovation#{self.innovation_project_id_placeholder}"
        return (
            f"Assignment: {self.user.first_name} {self.user.last_name} "
            f"→ {project} ({self.track})"
        )