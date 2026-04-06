"""
Innovation Track serializers — input validation and output formatting.

Same pattern as launch serializers:
    - Input serializers (plain Serializer) for create/update operations
    - Output serializers (ModelSerializer) for response formatting
"""

from rest_framework import serializers

from apps.innovation.models import InnovationPreference, InnovationProject, Proposals


# ══════════════════════════════════════════════
# Input Serializers
# ══════════════════════════════════════════════


class SubmitProposalSerializer(serializers.Serializer):
    """Input DTO for submitting an Innovation proposal."""

    title = serializers.CharField(
        max_length=200,
        help_text="Title of the proposed project.",
    )
    description = serializers.CharField(
        help_text="Detailed description of the proposed project.",
    )
    tech_stack = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Tech stack for the proposed project.",
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


class PreferenceItemSerializer(serializers.Serializer):
    """A single preference entry: project_id + rank."""

    project_id = serializers.IntegerField(
        help_text="ID of the InnovationProject to rank.",
    )
    rank = serializers.IntegerField(
        min_value=1,
        max_value=3,
        help_text="Rank (1 = top choice, 2, 3).",
    )


class SubmitPreferencesSerializer(serializers.Serializer):
    """Input DTO for submitting Innovation preferences."""

    preferences = serializers.ListField(
        child=PreferenceItemSerializer(),
        min_length=1,
        max_length=3,
        help_text="List of 1-3 ranked project preferences.",
    )


class AssignToInnovationSerializer(serializers.Serializer):
    """Input DTO for assigning a student to an Innovation project."""

    user_id = serializers.IntegerField(
        help_text="User ID of the student to assign.",
    )
    project_id = serializers.IntegerField(
        help_text="ID of the InnovationProject to assign to.",
    )


# ══════════════════════════════════════════════
# Output Serializers
# ══════════════════════════════════════════════


class ProposalListSerializer(serializers.ModelSerializer):
    """Output for listing proposals (Admin/Ops view)."""

    proposer_name = serializers.SerializerMethodField()
    proposer_email = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Proposals
        fields = [
            "id",
            "cycle",
            "proposer",
            "proposer_name",
            "proposer_email",
            "title",
            "description",
            "tech_stack",
            "max_members",
            "status",
            "status_display",
            "submitted_at",
        ]
        read_only_fields = fields

    def get_proposer_name(self, obj):
        return f"{obj.proposer.first_name} {obj.proposer.last_name}"

    def get_proposer_email(self, obj):
        return obj.proposer.email

    def get_status_display(self, obj):
        return obj.get_status_display()


class ProposalStudentSerializer(serializers.ModelSerializer):
    """Output for student viewing their own proposal."""

    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Proposals
        fields = [
            "id",
            "title",
            "description",
            "tech_stack",
            "max_members",
            "status",
            "status_display",
            "submitted_at",
        ]
        read_only_fields = fields

    def get_status_display(self, obj):
        return obj.get_status_display()


class InnovationProjectListSerializer(serializers.ModelSerializer):
    """Output for listing approved Innovation projects."""

    lead_name = serializers.SerializerMethodField()
    lead_email = serializers.SerializerMethodField()
    preference_count = serializers.SerializerMethodField()
    assigned_count = serializers.SerializerMethodField()

    class Meta:
        model = InnovationProject
        fields = [
            "id",
            "title",
            "lead",
            "lead_name",
            "lead_email",
            "max_members",
            "preference_count",
            "assigned_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_lead_name(self, obj):
        return f"{obj.lead.first_name} {obj.lead.last_name}"

    def get_lead_email(self, obj):
        return obj.lead.email

    def get_preference_count(self, obj):
        return obj.preferences.count()

    def get_assigned_count(self, obj):
        return obj.assignments.count()


class InnovationProjectDetailSerializer(serializers.ModelSerializer):
    """Full detail for a single Innovation project."""

    lead_name = serializers.SerializerMethodField()
    lead_email = serializers.SerializerMethodField()
    proposal_id = serializers.SerializerMethodField()
    preference_count = serializers.SerializerMethodField()
    assigned_count = serializers.SerializerMethodField()

    class Meta:
        model = InnovationProject
        fields = [
            "id",
            "proposal_id",
            "cycle",
            "title",
            "lead",
            "lead_name",
            "lead_email",
            "max_members",
            "preference_count",
            "assigned_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_lead_name(self, obj):
        return f"{obj.lead.first_name} {obj.lead.last_name}"

    def get_lead_email(self, obj):
        return obj.lead.email

    def get_proposal_id(self, obj):
        return obj.proposal_id

    def get_preference_count(self, obj):
        return obj.preferences.count()

    def get_assigned_count(self, obj):
        return obj.assignments.count()


class PreferenceStudentSerializer(serializers.ModelSerializer):
    """Output for student viewing their own preferences."""

    project_title = serializers.SerializerMethodField()

    class Meta:
        model = InnovationPreference
        fields = [
            "id",
            "project",
            "project_title",
            "rank",
            "submitted_at",
        ]
        read_only_fields = fields

    def get_project_title(self, obj):
        return obj.project.title


class PreferenceAdminSerializer(serializers.ModelSerializer):
    """Output for Admin/Ops viewing preferences for a project."""

    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    project_title = serializers.SerializerMethodField()

    class Meta:
        model = InnovationPreference
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "project",
            "project_title",
            "rank",
            "submitted_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_user_email(self, obj):
        return obj.user.email

    def get_project_title(self, obj):
        return obj.project.title