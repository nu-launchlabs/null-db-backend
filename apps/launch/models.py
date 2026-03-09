from django.db import models
from utils.mixins import TimestampMixin

class LaunchProject(TimestampMixin):

    # Foreign keys
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="launch_projects"
    )
    team = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="launch_projects"
    )

    # Non-key attributes
    title = models.CharField(
        max_length=200,
        help_text="Title of Launch Project"
    )
    description = models.TextField(
        help_text="Description of Launch Project"
    )
    requirements = models.TextField(
        null=True,
        blank=True,
        help_text='Requirements for application to project, e.g., "proficiency with Django"'
    )
    max_members = models.IntegerField(
        default=4
    )

    class Meta:
        db_table = "launch_projects"
        ordering = ["-created_at"]
        verbose_name = "Launch Project"
        verbose_name_plural = "Launch Projects"

    def __str__(self):
        return f"Launch Project: {self.title} — {self.team.first_name} {self.team.last_name} ({self.team.email})"

class LaunchApplication(TimestampMixin):
    
    # Foreign keys
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="launch_applications"
    )
    project = models.ForeignKey(
        LaunchProject,
        on_delete=models.CASCADE,
        related_name="launch_applications"
    )
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="launch_applications"
    )

    # Non-key attributes
    resume = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Link to applicant's resume"
    )
    portfolio = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Link to applicant's portfolio"
    )

    responses = models.JSONField(
        null=True,
        blank=True,
        help_text="Responses to application"
    )

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        FILTERED = "FILTERED", "Filtered"
        SENT_TO_TEAM = "SENT_TO_TEAM", "Sent to team"
        SELECTED = "SELECTED", "Selected"
        NOT_SELECTED = "NOT_SELECTED", "Not selected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED
    )

    class Meta:
        db_table = "launch_applications"
        ordering = ["-created_at"]
        verbose_name = "Launch Application"
        verbose_name_plural = "Launch Applications"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project", "cycle"],
                name="unique_la_per_user_per_project_per_cycle"
            )
        ]
