"""
Launch Track serializers — input validation and output formatting.

Serializers here follow the same pattern as accounts/cycles:
    - Input serializers (plain Serializer) for create/update operations
    - Output serializers (ModelSerializer) for response formatting
"""

from rest_framework import serializers

from apps.launch.models import LaunchApplication, LaunchCandidate, LaunchProject


# ══════════════════════════════════════════════
# Input Serializers
# ══════════════════════════════════════════════


class CreateLaunchProjectSerializer(serializers.Serializer):
    """Input DTO for creating a Launch Project."""

    team_id = serializers.IntegerField(
        help_text="User ID of the LAUNCH_TEAM member who owns this project.",
    )
    title = serializers.CharField(
        max_length=200,
        help_text="Project title.",
    )
    description = serializers.CharField(
        help_text="Detailed project description.",
    )
    requirements = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Skills or prerequisites for applicants.",
    )
    max_members = serializers.IntegerField(
        required=False,
        default=4,
        min_value=1,
        max_value=20,
        help_text="Maximum team size (1-20).",
    )

    def validate_title(self, value):
        return value.strip()

    def validate_description(self, value):
        return value.strip()


class ApplyToLaunchProjectSerializer(serializers.Serializer):
    """Input DTO for a student applying to a Launch Project."""

    resume = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Link to resume (Google Drive, Dropbox, etc.).",
    )
    portfolio = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Link to portfolio or personal website.",
    )
    responses = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Answers to project-specific application questions.",
    )


class BulkFilterApplicationsSerializer(serializers.Serializer):
    """Input DTO for bulk-filtering applications."""

    application_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of LaunchApplication IDs to mark as FILTERED.",
    )


class SendToTeamSerializer(serializers.Serializer):
    """Input DTO for sending filtered applications to a Launch Team."""

    application_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of LaunchApplication IDs to send to the Launch Team.",
    )


# ══════════════════════════════════════════════
# Output Serializers
# ══════════════════════════════════════════════


class LaunchProjectListSerializer(serializers.ModelSerializer):
    """Lightweight output for project listing."""

    team_name = serializers.SerializerMethodField()
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = LaunchProject
        fields = [
            "id",
            "title",
            "description",
            "requirements",
            "max_members",
            "team",
            "team_name",
            "application_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_team_name(self, obj):
        return f"{obj.team.first_name} {obj.team.last_name}"

    def get_application_count(self, obj):
        return obj.launch_applications.count()


class LaunchProjectDetailSerializer(serializers.ModelSerializer):
    """Full detail output for a single project."""

    team_name = serializers.SerializerMethodField()
    team_email = serializers.SerializerMethodField()
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = LaunchProject
        fields = [
            "id",
            "cycle",
            "team",
            "team_name",
            "team_email",
            "title",
            "description",
            "requirements",
            "max_members",
            "application_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_team_name(self, obj):
        return f"{obj.team.first_name} {obj.team.last_name}"

    def get_team_email(self, obj):
        return obj.team.email

    def get_application_count(self, obj):
        return obj.launch_applications.count()


class LaunchApplicationListSerializer(serializers.ModelSerializer):
    """Output for listing applications (Admin/Ops view)."""

    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()
    project_title = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = LaunchApplication
        fields = [
            "id",
            "user",
            "applicant_name",
            "applicant_email",
            "project",
            "project_title",
            "resume",
            "portfolio",
            "responses",
            "status",
            "status_display",
            "created_at",
        ]
        read_only_fields = fields

    def get_applicant_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_applicant_email(self, obj):
        return obj.user.email

    def get_project_title(self, obj):
        return obj.project.title

    def get_status_display(self, obj):
        return obj.get_status_display()


class LaunchApplicationStudentSerializer(serializers.ModelSerializer):
    """Output for student viewing their own applications."""

    project_title = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = LaunchApplication
        fields = [
            "id",
            "project",
            "project_title",
            "resume",
            "portfolio",
            "responses",
            "status",
            "status_display",
            "created_at",
        ]
        read_only_fields = fields

    def get_project_title(self, obj):
        return obj.project.title

    def get_status_display(self, obj):
        return obj.get_status_display()


class LaunchCandidateListSerializer(serializers.ModelSerializer):
    """Output for Launch Team viewing their candidates."""

    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()
    portfolio = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = LaunchCandidate
        fields = [
            "id",
            "application",
            "project",
            "applicant_name",
            "applicant_email",
            "resume",
            "portfolio",
            "responses",
            "status",
            "status_display",
            "selected_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_applicant_name(self, obj):
        u = obj.application.user
        return f"{u.first_name} {u.last_name}"

    def get_applicant_email(self, obj):
        return obj.application.user.email

    def get_resume(self, obj):
        return obj.application.resume

    def get_portfolio(self, obj):
        return obj.application.portfolio

    def get_responses(self, obj):
        return obj.application.responses

    def get_status_display(self, obj):
        return obj.get_status_display()