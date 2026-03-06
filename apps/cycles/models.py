"""
Application Cycle model — semester container with independent track toggles.

No linear state machine. Admin controls two independent toggles:
    - launch_open: students can apply to Launch projects
    - innovation_open: students can propose projects + rank preferences

Admin/Ops can assign students, manage projects, and review applications
at any time while the cycle is active — regardless of toggle state.

Only one cycle can be active at a time (enforced in service layer).
"""

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