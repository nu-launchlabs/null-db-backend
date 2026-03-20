"""
Launch Track views — thin controllers that delegate to LaunchService.

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
    IsAdmin,
    IsAdminOrOpsChair,
    IsGIComplete,
    IsLaunchTeam,
    IsStudentUser,
)
from apps.audit.services import AuditService
from apps.launch.permissions import IsLaunchTeamForProject
from apps.launch.serializers import (
    ApplyToLaunchProjectSerializer,
    BulkFilterApplicationsSerializer,
    CreateLaunchProjectSerializer,
    LaunchApplicationListSerializer,
    LaunchApplicationStudentSerializer,
    LaunchCandidateListSerializer,
    LaunchProjectDetailSerializer,
    LaunchProjectListSerializer,
    SendToTeamSerializer,
)
from apps.launch.services import LaunchService


# ══════════════════════════════════════════════
# Project Management (Admin)
# ══════════════════════════════════════════════


@extend_schema(tags=["Launch — Projects"])
class CreateLaunchProjectView(APIView):
    """
    POST /api/v1/launch/projects/
    Create a new Launch Project for the active cycle. Admin only.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        request=CreateLaunchProjectSerializer,
        responses={201: LaunchProjectDetailSerializer},
        summary="Create a Launch Project",
        description=(
            "Creates a new project linked to a LAUNCH_TEAM user and "
            "the current active cycle. Projects can be created anytime."
        ),
    )
    def post(self, request):
        ser = CreateLaunchProjectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        project = LaunchService.create_project(
            team_id=ser.validated_data["team_id"],
            title=ser.validated_data["title"],
            description=ser.validated_data["description"],
            requirements=ser.validated_data.get("requirements", ""),
            max_members=ser.validated_data.get("max_members", 4),
            created_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Launch project created.",
                "project": LaunchProjectDetailSerializer(project).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Launch — Projects"])
class LaunchProjectListView(APIView):
    """
    GET /api/v1/launch/projects/
    List all Launch projects for the active cycle.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: LaunchProjectListSerializer(many=True)},
        summary="List Launch projects",
        description="Returns all Launch projects for the current active cycle.",
    )
    def get(self, request):
        projects = LaunchService.list_projects_for_active_cycle()
        return Response(LaunchProjectListSerializer(projects, many=True).data)


@extend_schema(tags=["Launch — Projects"])
class LaunchProjectDetailView(APIView):
    """
    GET /api/v1/launch/projects/{project_id}/
    Get full details of a Launch project.

    DELETE /api/v1/launch/projects/{project_id}/
    Delete a Launch project (Admin only).
    """

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @extend_schema(
        responses={200: LaunchProjectDetailSerializer},
        summary="Get Launch project detail",
    )
    def get(self, request, project_id):
        project = LaunchService.get_project(project_id=project_id)
        return Response(LaunchProjectDetailSerializer(project).data)

    @extend_schema(
        summary="Delete a Launch project",
        description="Admin only. Cannot delete if selected candidates exist.",
        responses={200: None},
    )
    def delete(self, request, project_id):
        LaunchService.delete_project(
            project_id=project_id,
            deleted_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )
        return Response(
            {"message": "Launch project deleted."},
            status=status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════
# Student Application
# ══════════════════════════════════════════════


@extend_schema(tags=["Launch — Applications"])
class ApplyToProjectView(APIView):
    """
    POST /api/v1/launch/projects/{project_id}/apply/
    Student applies to a Launch Project.
    Must have completed GI form.
    """

    permission_classes = [IsAuthenticated, IsStudentUser, IsGIComplete]

    @extend_schema(
        request=ApplyToLaunchProjectSerializer,
        responses={201: LaunchApplicationStudentSerializer},
        summary="Apply to a Launch project",
        description=(
            "Submit an application. Requires: student role, GI complete, "
            "launch_open=True, no duplicate, not already assigned."
        ),
    )
    def post(self, request, project_id):
        ser = ApplyToLaunchProjectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        application = LaunchService.apply_to_project(
            user=request.user,
            project_id=project_id,
            resume=ser.validated_data.get("resume", ""),
            portfolio=ser.validated_data.get("portfolio", ""),
            responses=ser.validated_data.get("responses", {}),
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Application submitted successfully.",
                "application": LaunchApplicationStudentSerializer(
                    application
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Launch — Applications"])
class MyApplicationsView(APIView):
    """
    GET /api/v1/launch/my-applications/
    View own Launch applications for the current cycle.
    """

    permission_classes = [IsAuthenticated, IsStudentUser]

    @extend_schema(
        responses={200: LaunchApplicationStudentSerializer(many=True)},
        summary="View my Launch applications",
    )
    def get(self, request):
        apps = LaunchService.get_student_applications(user=request.user)
        return Response(
            LaunchApplicationStudentSerializer(apps, many=True).data
        )


# ══════════════════════════════════════════════
# Admin/Ops: View Applicants, Filter, Send to Team
# ══════════════════════════════════════════════


@extend_schema(tags=["Launch — Admin"])
class ProjectApplicantsView(APIView):
    """
    GET /api/v1/launch/projects/{project_id}/applicants/
    View all applicants for a specific project. Admin/Ops Chair.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                required=False,
                description="Filter by status (SUBMITTED, FILTERED, etc.)",
            ),
        ],
        responses={200: LaunchApplicationListSerializer(many=True)},
        summary="View applicants for a project",
        description="Returns all applications for the given project, optionally filtered by status.",
    )
    def get(self, request, project_id):
        status_filter = request.query_params.get("status")
        apps = LaunchService.get_applicants_for_project(
            project_id=project_id,
            status_filter=status_filter,
        )
        return Response(
            LaunchApplicationListSerializer(apps, many=True).data
        )


@extend_schema(tags=["Launch — Admin"])
class FilterApplicationsView(APIView):
    """
    POST /api/v1/launch/applications/filter/
    Bulk mark applications as FILTERED. Admin/Ops Chair.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        request=BulkFilterApplicationsSerializer,
        responses={200: LaunchApplicationListSerializer(many=True)},
        summary="Filter applications",
        description="Mark SUBMITTED applications as FILTERED. Only SUBMITTED apps qualify.",
    )
    def post(self, request):
        ser = BulkFilterApplicationsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        filtered = LaunchService.filter_applications(
            application_ids=ser.validated_data["application_ids"],
            filtered_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": f"{len(filtered)} application(s) filtered.",
                "applications": LaunchApplicationListSerializer(
                    filtered, many=True
                ).data,
            }
        )


@extend_schema(tags=["Launch — Admin"])
class SendToTeamView(APIView):
    """
    POST /api/v1/launch/applications/send-to-team/
    Send FILTERED applications to Launch Team for review. Admin/Ops Chair.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        request=SendToTeamSerializer,
        responses={200: LaunchCandidateListSerializer(many=True)},
        summary="Send applications to Launch Team",
        description=(
            "Creates LaunchCandidate records and updates app status to SENT_TO_TEAM. "
            "Only FILTERED applications qualify."
        ),
    )
    def post(self, request):
        ser = SendToTeamSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        candidates = LaunchService.send_to_team(
            application_ids=ser.validated_data["application_ids"],
            sent_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": f"{len(candidates)} application(s) sent to team.",
                "candidates": LaunchCandidateListSerializer(
                    candidates, many=True
                ).data,
            }
        )


# ══════════════════════════════════════════════
# Launch Team: View & Act on Candidates
# ══════════════════════════════════════════════


@extend_schema(tags=["Launch — Team"])
class LaunchTeamCandidatesView(APIView):
    """
    GET /api/v1/launch/candidates/
    View candidates sent to this Launch Team member's projects.
    """

    permission_classes = [IsAuthenticated, IsLaunchTeam]

    @extend_schema(
        responses={200: LaunchCandidateListSerializer(many=True)},
        summary="View my candidates",
        description="Launch Team sees only candidates for their own projects.",
    )
    def get(self, request):
        candidates = LaunchService.get_candidates_for_team(
            team_user=request.user
        )
        return Response(
            LaunchCandidateListSerializer(candidates, many=True).data
        )


@extend_schema(tags=["Launch — Team"])
class SelectCandidateView(APIView):
    """
    POST /api/v1/launch/candidates/{candidate_id}/select/
    Launch Team selects a candidate → auto-creates Assignment.
    """

    permission_classes = [IsAuthenticated, IsLaunchTeam]

    @extend_schema(
        summary="Select a candidate",
        description=(
            "Marks candidate as SELECTED, creates Assignment (track=LAUNCH). "
            "If student has an Innovation assignment, it is replaced and a "
            "warning is returned."
        ),
    )
    def post(self, request, candidate_id):
        candidate, assignment, warning = LaunchService.select_candidate(
            candidate_id=candidate_id,
            selected_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        response_data = {
            "message": "Candidate selected and assigned.",
            "candidate_id": candidate.id,
            "assignment_id": assignment.id,
            "applicant_email": candidate.application.user.email,
            "project_title": candidate.project.title,
        }

        if warning:
            response_data["warning"] = warning

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Launch — Team"])
class RejectCandidateView(APIView):
    """
    POST /api/v1/launch/candidates/{candidate_id}/reject/
    Launch Team rejects a candidate.
    """

    permission_classes = [IsAuthenticated, IsLaunchTeam]

    @extend_schema(
        summary="Reject a candidate",
        description="Marks candidate as REJECTED, app status as NOT_SELECTED.",
    )
    def post(self, request, candidate_id):
        candidate = LaunchService.reject_candidate(
            candidate_id=candidate_id,
            rejected_by=request.user,
            ip_address=AuditService.get_ip_from_request(request),
        )

        return Response(
            {
                "message": "Candidate rejected.",
                "candidate_id": candidate.id,
                "applicant_email": candidate.application.user.email,
            }
        )