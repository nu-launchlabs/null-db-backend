"""
Innovation Track views — thin controllers that delegate to InnovationService.

Rules:
    1. Parse & validate input (via serializer)
    2. Call service method
    3. Return response

NO business logic in views.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    IsAdminOrOpsChair,
    IsGIComplete,
    IsStudentUser,
)
from apps.audit.services import AuditService
from apps.innovation.serializers import (
    AssignToInnovationSerializer,
    InnovationProjectDetailSerializer,
    InnovationProjectListSerializer,
    PreferenceAdminSerializer,
    PreferenceStudentSerializer,
    ProposalListSerializer,
    ProposalStudentSerializer,
    SubmitPreferencesSerializer,
    SubmitProposalSerializer,
)
from apps.innovation.services import InnovationService


# ══════════════════════════════════════════════
# Proposals
# ══════════════════════════════════════════════


@extend_schema(tags=["Innovation — Proposals"])
class SubmitProposalView(APIView):
    """
    POST /api/v1/innovation/proposals/
    Student submits an Innovation proposal.
    """

    permission_classes = [IsAuthenticated, IsStudentUser, IsGIComplete]

    @extend_schema(
        request=SubmitProposalSerializer,
        responses={201: ProposalStudentSerializer},
        summary="Submit an Innovation proposal",
        description=(
            "Submit a project proposal. Requires: student role, GI complete, "
            "innovation_open=True, one per cycle, not already assigned."
        ),
    )
    def post(self, request):
        ser = SubmitProposalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        proposal = InnovationService.submit_proposal(
            user=request.user,
            title=ser.validated_data["title"],
            description=ser.validated_data["description"],
            tech_stack=ser.validated_data.get("tech_stack", ""),
            max_members=ser.validated_data.get("max_members", 4),
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Proposal submitted successfully.",
                "proposal": ProposalStudentSerializer(proposal).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Innovation — Proposals"])
class MyProposalView(APIView):
    """
    GET /api/v1/innovation/my-proposal/
    Student views their own proposal for the current cycle.
    """

    permission_classes = [IsAuthenticated, IsStudentUser]

    @extend_schema(
        responses={200: ProposalStudentSerializer},
        summary="View my proposal",
    )
    def get(self, request):
        proposal = InnovationService.get_student_proposal(user=request.user)
        if not proposal:
            return Response(
                {"message": "No proposal found for the current cycle."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProposalStudentSerializer(proposal).data)


@extend_schema(tags=["Innovation — Proposals"])
class ProposalListView(APIView):
    """
    GET /api/v1/innovation/proposals/
    Admin/Ops lists all proposals for the active cycle.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                required=False,
                description="Filter by status (SUBMITTED, APPROVED, REJECTED).",
            ),
        ],
        responses={200: ProposalListSerializer(many=True)},
        summary="List all proposals",
        description="Admin/Ops view of all proposals for the active cycle.",
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        proposals = InnovationService.list_proposals_for_active_cycle(
            status_filter=status_filter,
        )
        return Response(ProposalListSerializer(proposals, many=True).data)


@extend_schema(tags=["Innovation — Proposals"])
class ApproveProposalView(APIView):
    """
    POST /api/v1/innovation/proposals/{proposal_id}/approve/
    Admin/Ops approves a proposal → creates InnovationProject.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        summary="Approve a proposal",
        description=(
            "Approves a SUBMITTED proposal and creates an InnovationProject. "
            "The proposer becomes the project lead."
        ),
    )
    def post(self, request, proposal_id):
        proposal, project = InnovationService.approve_proposal(
            proposal_id=proposal_id,
            approved_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Proposal approved. Innovation project created.",
                "proposal": ProposalListSerializer(proposal).data,
                "project": InnovationProjectDetailSerializer(project).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Innovation — Proposals"])
class RejectProposalView(APIView):
    """
    POST /api/v1/innovation/proposals/{proposal_id}/reject/
    Admin/Ops rejects a proposal.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        summary="Reject a proposal",
        description=(
            "Rejects a SUBMITTED proposal. The proposer can then "
            "submit preferences for other projects."
        ),
    )
    def post(self, request, proposal_id):
        proposal = InnovationService.reject_proposal(
            proposal_id=proposal_id,
            rejected_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Proposal rejected.",
                "proposal": ProposalListSerializer(proposal).data,
            },
            status=status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════
# Innovation Projects
# ══════════════════════════════════════════════


@extend_schema(tags=["Innovation — Projects"])
class InnovationProjectListView(APIView):
    """
    GET /api/v1/innovation/projects/
    List all approved Innovation projects for the active cycle.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: InnovationProjectListSerializer(many=True)},
        summary="List Innovation projects",
        description="Returns all approved Innovation projects for the current cycle.",
    )
    def get(self, request):
        projects = InnovationService.list_projects_for_active_cycle()
        return Response(
            InnovationProjectListSerializer(projects, many=True).data
        )


@extend_schema(tags=["Innovation — Projects"])
class InnovationProjectDetailView(APIView):
    """
    GET /api/v1/innovation/projects/{project_id}/
    Get full detail of an Innovation project.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: InnovationProjectDetailSerializer},
        summary="Get Innovation project detail",
    )
    def get(self, request, project_id):
        project = InnovationService.get_project(project_id=project_id)
        return Response(InnovationProjectDetailSerializer(project).data)


# ══════════════════════════════════════════════
# Preferences
# ══════════════════════════════════════════════


@extend_schema(tags=["Innovation — Preferences"])
class SubmitPreferencesView(APIView):
    """
    POST /api/v1/innovation/preferences/
    Student submits ranked preferences (1-3 Innovation projects).

    PUT /api/v1/innovation/preferences/
    Student updates preferences (same logic, replaces existing).
    """

    permission_classes = [IsAuthenticated, IsStudentUser, IsGIComplete]

    @extend_schema(
        request=SubmitPreferencesSerializer,
        responses={201: PreferenceStudentSerializer(many=True)},
        summary="Submit Innovation preferences",
        description=(
            "Submit 1-3 ranked project preferences. Replaces any "
            "existing preferences. Requires: student role, GI complete, "
            "innovation_open=True, not assigned, no active proposal."
        ),
    )
    def post(self, request):
        ser = SubmitPreferencesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        prefs = InnovationService.submit_preferences(
            user=request.user,
            preferences=ser.validated_data["preferences"],
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Preferences submitted successfully.",
                "preferences": PreferenceStudentSerializer(
                    prefs, many=True
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=SubmitPreferencesSerializer,
        responses={200: PreferenceStudentSerializer(many=True)},
        summary="Update Innovation preferences",
        description="Same as POST — replaces existing preferences.",
    )
    def put(self, request):
        ser = SubmitPreferencesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        prefs = InnovationService.submit_preferences(
            user=request.user,
            preferences=ser.validated_data["preferences"],
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Preferences updated successfully.",
                "preferences": PreferenceStudentSerializer(
                    prefs, many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Innovation — Preferences"])
class MyPreferencesView(APIView):
    """
    GET /api/v1/innovation/my-preferences/
    Student views their own preferences for the current cycle.
    """

    permission_classes = [IsAuthenticated, IsStudentUser]

    @extend_schema(
        responses={200: PreferenceStudentSerializer(many=True)},
        summary="View my preferences",
    )
    def get(self, request):
        prefs = InnovationService.get_student_preferences(user=request.user)
        return Response(PreferenceStudentSerializer(prefs, many=True).data)


@extend_schema(tags=["Innovation — Preferences"])
class ProjectPreferencesView(APIView):
    """
    GET /api/v1/innovation/projects/{project_id}/preferences/
    Admin/Ops views who ranked this project and at what rank.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        responses={200: PreferenceAdminSerializer(many=True)},
        summary="View preferences for a project",
        description="Shows all students who ranked this project, with rank breakdown.",
    )
    def get(self, request, project_id):
        prefs = InnovationService.get_preferences_for_project(
            project_id=project_id,
        )
        return Response(PreferenceAdminSerializer(prefs, many=True).data)


# ══════════════════════════════════════════════
# Assignment (Admin/Ops)
# ══════════════════════════════════════════════


@extend_schema(tags=["Innovation — Assignment"])
class AssignToInnovationView(APIView):
    """
    POST /api/v1/innovation/assign/
    Admin/Ops assigns a student to an Innovation project.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        request=AssignToInnovationSerializer,
        summary="Assign student to Innovation project",
        description=(
            "Creates an Assignment row (track=INNOVATION). "
            "Not gated by innovation_open toggle — admin can assign anytime. "
            "Checks for existing assignments and team capacity."
        ),
    )
    def post(self, request):
        ser = AssignToInnovationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        assignment = InnovationService.assign_to_project(
            user_id=ser.validated_data["user_id"],
            project_id=ser.validated_data["project_id"],
            assigned_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Student assigned to Innovation project.",
                "assignment_id": assignment.id,
                "student_email": assignment.user.email,
                "project_title": assignment.innovation_project.title,
                "track": assignment.track,
            },
            status=status.HTTP_201_CREATED,
        )