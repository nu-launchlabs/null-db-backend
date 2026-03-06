"""
Audit views — read-only access to audit trail.

Only Admin and Ops Chair can view audit logs.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrOpsChair
from apps.audit.serializers import AuditLogSerializer
from apps.audit.services import AuditService
from utils.pagination import StandardPagination


@extend_schema(tags=["Audit"])
class AuditLogListView(APIView):
    """
    GET /api/v1/audit/logs/
    View audit trail with optional filters. Admin or Ops Chair.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        summary="List audit logs",
        description=(
            "Returns the audit trail with optional filtering by action, "
            "actor, and target type. Results are paginated."
        ),
        parameters=[
            OpenApiParameter(
                name="action",
                type=str,
                description="Filter by action type (e.g. USER_REGISTERED, PHASE_ADVANCED)",
            ),
            OpenApiParameter(
                name="actor_id",
                type=int,
                description="Filter by actor user ID",
            ),
            OpenApiParameter(
                name="target_type",
                type=str,
                description='Filter by target type (e.g. "User", "ApplicationCycle")',
            ),
        ],
        responses={200: AuditLogSerializer(many=True)},
    )
    def get(self, request):
        logs = AuditService.get_logs(
            action=request.query_params.get("action"),
            actor_id=request.query_params.get("actor_id"),
            target_type=request.query_params.get("target_type"),
        )

        # Manual pagination for APIView
        paginator = StandardPagination()
        page = paginator.paginate_queryset(logs, request)

        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)