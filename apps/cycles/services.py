"""
Cycle service layer — manages application cycle lifecycle.

Core responsibilities:
    - Create new cycles (only one active at a time)
    - Toggle launch_open / innovation_open independently
    - Close a cycle (deactivate)
    - Retrieve current active cycle
    - Generate cycle statistics
"""

import logging

from django.db import transaction

from apps.accounts.models import User
from apps.cycles.models import ApplicationCycle
from utils.exceptions import BusinessLogicError, ConflictError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class CycleService:
    """Manages the application cycle lifecycle."""

    # Create Cycle
    @staticmethod
    @transaction.atomic
    def create_cycle(*, name: str, description: str = "", created_by: User) -> ApplicationCycle:
        """
        Create a new application cycle.

        Business rules:
            - Only one active cycle at a time
            - New cycle starts with both toggles OFF
            - Name must be unique
        """
        if ApplicationCycle.objects.filter(is_active=True).exists():
            raise ConflictError(
                "An active cycle already exists. Close the current cycle "
                "before creating a new one."
            )

        cycle = ApplicationCycle.objects.create(
            name=name.strip(),
            description=description.strip(),
            is_active=True,
            launch_open=False,
            innovation_open=False,
        )

        logger.info(
            "Cycle created: '%s' by %s", cycle.name, created_by.email
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="CYCLE_CREATED",
            actor=created_by,
            target_type="ApplicationCycle",
            target_id=cycle.id,
            metadata={"cycle_name": cycle.name},
        )

        return cycle

    # Update Toggles
    @staticmethod
    @transaction.atomic
    def update_toggles(
        *,
        cycle_id: int,
        updated_by: User,
        launch_open: bool = None,
        innovation_open: bool = None,
    ) -> ApplicationCycle:
        """
        Update one or both track toggles independently.

        Admin can:
            - Open Launch while Innovation is closed (or vice versa)
            - Open both simultaneously
            - Close one while the other stays open
            - Close both

        No dependencies between toggles.
        """
        try:
            cycle = ApplicationCycle.objects.select_for_update().get(id=cycle_id)
        except ApplicationCycle.DoesNotExist:
            raise ResourceNotFoundError(f"Cycle with id {cycle_id} not found.")

        if not cycle.is_active:
            raise BusinessLogicError("Cannot update toggles on an inactive cycle.")

        changes = {}
        update_fields = ["updated_at"]

        if launch_open is not None and launch_open != cycle.launch_open:
            old_val = cycle.launch_open
            cycle.launch_open = launch_open
            update_fields.append("launch_open")
            changes["launch_open"] = {"old": old_val, "new": launch_open}

        if innovation_open is not None and innovation_open != cycle.innovation_open:
            old_val = cycle.innovation_open
            cycle.innovation_open = innovation_open
            update_fields.append("innovation_open")
            changes["innovation_open"] = {"old": old_val, "new": innovation_open}

        if not changes:
            # Nothing actually changed
            return cycle

        cycle.save(update_fields=update_fields)

        logger.info(
            "Cycle '%s' toggles updated by %s: %s",
            cycle.name,
            updated_by.email,
            changes,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="CYCLE_TOGGLES_UPDATED",
            actor=updated_by,
            target_type="ApplicationCycle",
            target_id=cycle.id,
            metadata={
                "cycle_name": cycle.name,
                "changes": changes,
            },
        )

        return cycle

    # Close Cycle
    @staticmethod
    @transaction.atomic
    def close_cycle(*, cycle_id: int, closed_by: User) -> ApplicationCycle:
        """
        Close the cycle — sets is_active=False and turns off all toggles.

        This is a one-way operation. A closed cycle cannot be reopened.
        To start a new semester, create a new cycle.
        """
        try:
            cycle = ApplicationCycle.objects.select_for_update().get(id=cycle_id)
        except ApplicationCycle.DoesNotExist:
            raise ResourceNotFoundError(f"Cycle with id {cycle_id} not found.")

        if not cycle.is_active:
            raise BusinessLogicError("This cycle is already closed.")

        cycle.is_active = False
        cycle.launch_open = False
        cycle.innovation_open = False
        cycle.save(update_fields=[
            "is_active", "launch_open", "innovation_open", "updated_at"
        ])

        logger.info(
            "Cycle '%s' closed by %s", cycle.name, closed_by.email
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="CYCLE_CLOSED",
            actor=closed_by,
            target_type="ApplicationCycle",
            target_id=cycle.id,
            metadata={"cycle_name": cycle.name},
        )

        return cycle

    # Query Helpers
    @staticmethod
    def get_current_cycle() -> ApplicationCycle:
        """
        Get the current active cycle.

        Raises ResourceNotFoundError if no active cycle exists.
        """
        try:
            return ApplicationCycle.objects.get(is_active=True)
        except ApplicationCycle.DoesNotExist:
            raise ResourceNotFoundError("No active application cycle found.")
        except ApplicationCycle.MultipleObjectsReturned:
            logger.error("Multiple active cycles found! Data integrity issue.")
            return ApplicationCycle.objects.filter(is_active=True).first()

    @staticmethod
    def get_cycle_by_id(cycle_id: int) -> ApplicationCycle:
        """Fetch a single cycle or raise 404."""
        try:
            return ApplicationCycle.objects.get(id=cycle_id)
        except ApplicationCycle.DoesNotExist:
            raise ResourceNotFoundError(f"Cycle with id {cycle_id} not found.")

    @staticmethod
    def get_all_cycles(queryset=None):
        """Return all cycles, optionally from a pre-filtered queryset."""
        if queryset is not None:
            return queryset
        return ApplicationCycle.objects.all()

    @staticmethod
    def get_cycle_stats(cycle_id: int) -> dict:
        """
        Generate statistics for a given cycle.
        """
        try:
            cycle = ApplicationCycle.objects.get(id=cycle_id)
        except ApplicationCycle.DoesNotExist:
            raise ResourceNotFoundError(f"Cycle with id {cycle_id} not found.")

        from apps.accounts.models import GeneralInterest

        total_users = User.objects.filter(
            role=User.Role.USER, is_active=True
        ).count()

        gi_completed = GeneralInterest.objects.filter(cycle=cycle).count()

        return {
            "cycle_id": cycle.id,
            "cycle_name": cycle.name,
            "is_active": cycle.is_active,
            "launch_open": cycle.launch_open,
            "innovation_open": cycle.innovation_open,
            "total_users": total_users,
            "gi_completed": gi_completed,
            "gi_pending": total_users - gi_completed,
            # Placeholders — populated in Phase 3 & 4
            "launch_apps": 0,
            "launch_assigned": 0,
            "innovation_proposals": 0,
            "innovation_assigned": 0,
            "unassigned_users": total_users - gi_completed,
        }