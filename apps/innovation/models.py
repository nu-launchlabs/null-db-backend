"""
Models related to NULL Innovation Projects. Models included:
    Proposals
    InnovationProject
    InnovationPreference
"""

from django.db import models

from utils.mixins import TimestampMixin

from .choices import ProposalStatus


class Proposals(TimestampMixin, models.Model):
    """
    Model for storing information about Innovation Proposals.
    """

    class Meta:
        db_table = "proposals"
        ordering = ["-submitted_at"]
        verbose_name = "Innovation Proposal"
        verbose_name_plural = "Innovation Proposals"

    # Foreign keys
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="proposals",
    )
    proposer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="proposals",
    )

    # Non-key attributes
    title = models.CharField(max_length=200, help_text="Title of Proposal")
    description = models.TextField(help_text="Description of proposed project")
    tech_stack = models.TextField(
        null=True,
        blank=True,
        help_text="Tech stack to use for this proposed project",
    )
    max_members = models.IntegerField(default=4)
    status = models.CharField(
        max_length=20,
        choices=ProposalStatus.choices,
        default=ProposalStatus.SUBMITTED,
        help_text="The status of the proposal, e.g., Submitted, Approved, etc",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proposal: {self.title} ({self.status})"


class InnovationProject(models.Model):
    """
    Created when an admin approves a Proposal.
    One-to-one with the proposal that originated it.
    """

    proposal = models.OneToOneField(
        "Proposals",
        on_delete=models.CASCADE,
        related_name="innovation_project",
    )
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="innovation_projects",
    )
    lead = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="led_innovation_projects",
    )
    title = models.CharField(max_length=200)
    max_members = models.IntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "innovation_projects"

    def __str__(self):
        return self.title


class InnovationPreference(models.Model):
    """
    Students rank their top 3 preferred Innovation projects.
    """

    RANK_CHOICES = [(1, "1"), (2, "2"), (3, "3")]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="innovation_preferences",
    )
    project = models.ForeignKey(
        InnovationProject,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="innovation_preferences",
    )
    rank = models.IntegerField(choices=RANK_CHOICES)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "innovation_preferences"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project", "cycle"],
                name="unique_user_project_cycle",
            ),
            models.UniqueConstraint(
                fields=["user", "rank", "cycle"],
                name="unique_user_rank_cycle",
            ),
            models.CheckConstraint(
                check=models.Q(rank__in=[1, 2, 3]),
                name="rank_must_be_1_2_or_3",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.project} (Rank {self.rank})"