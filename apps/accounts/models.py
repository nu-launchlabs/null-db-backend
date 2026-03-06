"""
Custom User model and General Interest model.

Key decisions:
    - AbstractUser gives us username/password/is_staff for free + Django Admin compat.
    - We override email to be the login field (USERNAME_FIELD).
    - Role is an enum stored as VARCHAR, not a separate roles table.
    - is_gi_complete is denormalized for fast permission checks.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.managers import UserManager
from utils.mixins import TimestampMixin


class User(AbstractUser, TimestampMixin):
    """
    Custom User model for NU Launch Labs.

    USERNAME_FIELD = email (not username).
    Role-based access via the `role` field.
    """

    class Role(models.TextChoices):

        ADMIN = "ADMIN", "Admin"
        OPS_CHAIR = "OPS_CHAIR", "Operations Chair"
        USER = "USER", "User"
        LAUNCH_TEAM = "LAUNCH_TEAM", "Launch Team"

    # Remove username field - we use email as the unique identifier
    username = None

    email = models.EmailField(
        unique=True,
        db_index=True,
        error_messages={"unique": "A user with this email already exists."},
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    is_gi_complete = models.BooleanField(
        default=False,
        help_text="True after user submits General Interest form for the active cycle.",
    )
    is_neu_email = models.BooleanField(
        default=True,
        help_text="False only for LAUNCH_TEAM members with non-NEU emails.",
    )

    # Auth config
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    # Computed Properties (model-level only)
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_ops_chair(self):
        return self.role == self.Role.OPS_CHAIR

    @property
    def is_launch_team(self):
        return self.role == self.Role.LAUNCH_TEAM

    @property
    def is_student(self):
        """USER role = Northeastern student."""
        return self.role == self.Role.USER


# General Interest Model (Phase 2)


class GeneralInterest(TimestampMixin, models.Model):
    """
    General Interest form submission.

    Each student submits one GI per cycle. Completing GI is required
    before applying to Launch or Innovation tracks.

    Business rules:
        - Only USER role can submit
        - Submitting sets user.is_gi_complete = True
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="general_interests",
    )
    cycle = models.ForeignKey(
        "cycles.ApplicationCycle",
        on_delete=models.CASCADE,
        related_name="general_interests",
    )
    graduation_year = models.IntegerField(
        help_text="Expected graduation year, e.g. 2027",
    )
    college = models.CharField(
        max_length=200,
        help_text='College within NEU, e.g. "Khoury College of Computer Sciences"',
    )
    major = models.CharField(
        max_length=200,
        help_text='Major/program, e.g. "Computer Science"',
    )
    skills = models.TextField(
        help_text="Technical and non-technical skills (free text).",
    )
    interest_areas = models.TextField(
        help_text="Areas of interest: product, engineering, design, marketing, etc.",
    )
    why_join = models.TextField(
        help_text="Why do you want to join NU Launch Labs?",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "general_interests"
        ordering = ["-submitted_at"]
        verbose_name = "General Interest"
        verbose_name_plural = "General Interests"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "cycle"],
                name="unique_gi_per_user_per_cycle",
            ),
        ]

    def __str__(self):
        return f"GI: {self.user.email} — {self.cycle.name}"