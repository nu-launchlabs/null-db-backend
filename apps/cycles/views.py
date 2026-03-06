"""
Cycle views — thin controllers for cycle management.

All business logic lives in CycleService.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin, IsAdminOrOpsChair
from apps.cycles.serializers import (
    CreateCycleSerializer,
    CycleDetailSerializer,
    CycleListSerializer,
    CycleStatsSerializer,
    UpdateCycleTogglesSerializer,
)
from apps.cycles.services import CycleService


@extend_schema(tags=["Cycles"])
class CreateCycleView(APIView):
    """
    POST /api/v1/cycles/
    Create a new application cycle. Admin only.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        request=CreateCycleSerializer,
        responses={201: CycleDetailSerializer},
        summary="Create a new application cycle",
        description=(
            "Creates a new cycle with both toggles OFF. "
            "Only one active cycle allowed at a time."
        ),
    )
    def post(self, request):
        serializer = CreateCycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cycle = CycleService.create_cycle(
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            created_by=request.user,
        )

        return Response(
            {
                "message": "Application cycle created.",
                "cycle": CycleDetailSerializer(cycle).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Cycles"])
class CurrentCycleView(APIView):
    """
    GET /api/v1/cycles/current/
    Get the current active cycle with toggle status.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CycleDetailSerializer},
        summary="Get current active cycle",
        description="Returns the currently active cycle and its toggle states.",
    )
    def get(self, request):
        cycle = CycleService.get_current_cycle()
        return Response(CycleDetailSerializer(cycle).data)


@extend_schema(tags=["Cycles"])
class UpdateCycleTogglesView(APIView):
    """
    PATCH /api/v1/cycles/{cycle_id}/toggles/
    Update track toggles independently. Admin only.

    Send only the toggles you want to change:
        {"launch_open": true}                     — opens Launch only
        {"innovation_open": false}                — closes Innovation only
        {"launch_open": true, "innovation_open": true}  — opens both
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        request=UpdateCycleTogglesSerializer,
        responses={200: CycleDetailSerializer},
        summary="Update cycle toggles",
        description=(
            "Independently toggle launch_open and/or innovation_open. "
            "Send only the fields you want to change. "
            "No dependencies between toggles — both can be on/off in any combination."
        ),
    )
    def patch(self, request, cycle_id):
        serializer = UpdateCycleTogglesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cycle = CycleService.update_toggles(
            cycle_id=cycle_id,
            updated_by=request.user,
            launch_open=serializer.validated_data.get("launch_open"),
            innovation_open=serializer.validated_data.get("innovation_open"),
        )

        return Response(
            {
                "message": "Cycle toggles updated.",
                "cycle": CycleDetailSerializer(cycle).data,
            }
        )


@extend_schema(tags=["Cycles"])
class CloseCycleView(APIView):
    """
    POST /api/v1/cycles/{cycle_id}/close/
    Close the cycle. Admin only. One-way operation.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        responses={200: CycleDetailSerializer},
        summary="Close application cycle",
        description=(
            "Closes the cycle — sets is_active=False and turns off all toggles. "
            "This is permanent. Create a new cycle for the next semester."
        ),
    )
    def post(self, request, cycle_id):
        cycle = CycleService.close_cycle(
            cycle_id=cycle_id,
            closed_by=request.user,
        )

        return Response(
            {
                "message": f"Cycle '{cycle.name}' has been closed.",
                "cycle": CycleDetailSerializer(cycle).data,
            }
        )


@extend_schema(tags=["Cycles"])
class CycleStatsView(APIView):
    """
    GET /api/v1/cycles/{cycle_id}/stats/
    Cycle statistics dashboard. Admin or Ops Chair.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        responses={200: CycleStatsSerializer},
        summary="Get cycle statistics",
        description="Returns counts of users, GI completions, and application stats.",
    )
    def get(self, request, cycle_id):
        stats = CycleService.get_cycle_stats(cycle_id=cycle_id)
        serializer = CycleStatsSerializer(stats)
        return Response(serializer.data)


@extend_schema(tags=["Cycles"])
@extend_schema_view(
    get=extend_schema(
        summary="List all cycles",
        description="Returns all cycles (active and closed). Admin or Ops Chair.",
        responses={200: CycleListSerializer(many=True)},
    ),
)
class CycleListView(APIView):
    """
    GET /api/v1/cycles/list/
    List all cycles. Admin or Ops Chair.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    def get(self, request):
        cycles = CycleService.get_all_cycles()

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            cycles = cycles.filter(is_active=is_active.lower() == "true")

        serializer = CycleListSerializer(cycles, many=True)
        return Response(serializer.data)