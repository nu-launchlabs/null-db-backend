"""
Innovation Track service layer — ALL business logic lives here.

Workflow:
    1. Student submits a proposal (one per person per cycle, GI done,
       innovation_open=True)
    2. Admin/Ops reviews proposals → approve (creates InnovationProject)
       or reject
    3. Students rank up to 3 approved InnovationProjects by preference
       (GI done, innovation_open=True, not assigned, no pending/approved
       proposal)
    4. Admin/Ops assigns students to Innovation projects anytime
       (creates Assignment row, conflict check against Launch)

Rules:
    - Views call services, never touch ORM directly.
    - Services raise BusinessLogicError / ConflictError for rule violations.
    - Services call AuditService.log() for every significant action.
"""

import logging
import smtplib

from django.db import transaction

from apps.accounts.models import User
from apps.cycles.models import Assignment
from apps.innovation.choices import ProposalStatus
from apps.innovation.models import InnovationPreference, InnovationProject, Proposals
from apps.notifications.services import send_notification_email
from utils.exceptions import (
    BusinessLogicError,
    ConflictError,
    ForbiddenError,
    ResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class InnovationService:
    """Handles all Innovation Track operations."""

    # ══════════════════════════════════════════════
    # Proposals
    # ══════════════════════════════════════════════

    @staticmethod
    @transaction.atomic
    def submit_proposal(
        *,
        user: User,
        title: str,
        description: str,
        tech_stack: str = "",
        max_members: int = 4,
        ip_address: str = None,
    ) -> Proposals:
        """
        Student submits an Innovation proposal.

        Business rules:
            - innovation_open must be True on the active cycle
            - GI must be complete (enforced at view level via IsGIComplete)
            - One proposal per student per cycle
            - Student must not already be assigned this cycle
        """
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        if not cycle.innovation_open:
            raise BusinessLogicError(
                "Innovation applications are not currently open."
            )

        # One proposal per student per cycle
        if Proposals.objects.filter(proposer=user, cycle=cycle).exists():
            raise ConflictError(
                "You have already submitted a proposal for this cycle."
            )

        # Cannot propose if already assigned
        if Assignment.objects.filter(user=user, cycle=cycle).exists():
            raise BusinessLogicError(
                "You are already assigned to a project this cycle. "
                "You cannot submit a proposal."
            )

        proposal = Proposals.objects.create(
            cycle=cycle,
            proposer=user,
            title=title.strip(),
            description=description.strip(),
            tech_stack=tech_stack.strip() if tech_stack else "",
            max_members=max_members,
            status=ProposalStatus.SUBMITTED,
        )

        logger.info(
            "Proposal submitted: '%s' by %s (cycle=%s)",
            title,
            user.email,
            cycle.name,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="PROPOSAL_SUBMITTED",
            actor=user,
            target_type="Proposals",
            target_id=proposal.id,
            metadata={
                "title": title,
                "cycle": cycle.name,
            },
            ip_address=ip_address,
        )

        return proposal

    @staticmethod
    def get_student_proposal(*, user: User):
        """Get the student's proposal for the current cycle (or None)."""
        from apps.cycles.services import CycleService

        try:
            cycle = CycleService.get_current_cycle()
        except ResourceNotFoundError:
            return None

        return Proposals.objects.filter(
            proposer=user, cycle=cycle
        ).select_related("cycle").first()

    @staticmethod
    def list_proposals_for_active_cycle(*, status_filter: str = None):
        """List all proposals for the current active cycle. Admin/Ops view."""
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        qs = (
            Proposals.objects.filter(cycle=cycle)
            .select_related("cycle", "proposer")
            .order_by("-submitted_at")
        )

        if status_filter:
            status_upper = status_filter.upper()
            valid = [s.value for s in ProposalStatus]
            if status_upper not in valid:
                raise BusinessLogicError(
                    f"Invalid status filter: {status_filter}. "
                    f"Valid values: {', '.join(valid)}"
                )
            qs = qs.filter(status=status_upper)

        return qs

    @staticmethod
    @transaction.atomic
    def approve_proposal(
        *,
        proposal_id: int,
        approved_by: User,
        ip_address: str = None,
    ) -> tuple:
        """
        Admin/Ops approves a proposal → creates InnovationProject.

        Returns:
            tuple: (Proposals, InnovationProject)

        Business rules:
            - Proposal must be in SUBMITTED status
            - Creates an InnovationProject linked to the proposal
            - Sets proposer as project lead
            - Does NOT auto-assign the proposer (assignment is separate)
        """
        try:
            proposal = Proposals.objects.select_related(
                "cycle", "proposer"
            ).get(id=proposal_id)
        except Proposals.DoesNotExist:
            raise ResourceNotFoundError(
                f"Proposal with id {proposal_id} not found."
            )

        if proposal.status != ProposalStatus.SUBMITTED:
            raise BusinessLogicError(
                f"Proposal is already {proposal.get_status_display()}. "
                f"Only SUBMITTED proposals can be approved."
            )

        # Update proposal status
        proposal.status = ProposalStatus.APPROVED
        proposal.save(update_fields=["status", "updated_at"])

        # Create InnovationProject
        project = InnovationProject.objects.create(
            proposal=proposal,
            cycle=proposal.cycle,
            lead=proposal.proposer,
            title=proposal.title,
            max_members=proposal.max_members,
        )

        logger.info(
            "Proposal approved: '%s' by %s → InnovationProject #%d",
            proposal.title,
            approved_by.email,
            project.id,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="PROPOSAL_APPROVED",
            actor=approved_by,
            target_type="Proposals",
            target_id=proposal.id,
            metadata={
                "title": proposal.title,
                "proposer_email": proposal.proposer.email,
                "innovation_project_id": project.id,
                "cycle": proposal.cycle.name,
            },
            ip_address=ip_address,
        )

        try:
            send_notification_email(
                subject=f"Proposal '{proposal.title}' approved!",
                recipient_email=proposal.proposer.email,
                plain_message=(
                    f"Hello {proposal.proposer.first_name},\n\n"
                    f"Congratulations! Your NU Launch Labs Innovation proposal has been approved.\n\n"
                    f"— NU Launch Labs"
                )
            )
        except smtplib.SMTPException:
            logger.error(
                "Unable to send approval email for proposal %d - %s",
                proposal.id,
                proposal.title
            )

        return proposal, project

    @staticmethod
    @transaction.atomic
    def reject_proposal(
        *,
        proposal_id: int,
        rejected_by: User,
        ip_address: str = None,
    ) -> Proposals:
        """
        Admin/Ops rejects a proposal.

        Business rules:
            - Proposal must be in SUBMITTED status
            - After rejection, proposer becomes eligible to submit preferences
        """
        try:
            proposal = Proposals.objects.select_related(
                "cycle", "proposer"
            ).get(id=proposal_id)
        except Proposals.DoesNotExist:
            raise ResourceNotFoundError(
                f"Proposal with id {proposal_id} not found."
            )

        if proposal.status != ProposalStatus.SUBMITTED:
            raise BusinessLogicError(
                f"Proposal is already {proposal.get_status_display()}. "
                f"Only SUBMITTED proposals can be rejected."
            )

        proposal.status = ProposalStatus.REJECTED
        proposal.save(update_fields=["status", "updated_at"])

        logger.info(
            "Proposal rejected: '%s' by %s",
            proposal.title,
            rejected_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="PROPOSAL_REJECTED",
            actor=rejected_by,
            target_type="Proposals",
            target_id=proposal.id,
            metadata={
                "title": proposal.title,
                "proposer_email": proposal.proposer.email,
                "cycle": proposal.cycle.name,
            },
            ip_address=ip_address,
        )

        try:
            send_notification_email(
                subject=f"Your proposal '{proposal.title}' was not approved",
                recipient_email=proposal.proposer.email,
                plain_message=(
                    f"Hi {proposal.proposer.first_name},\n\n"
                    f"Thank you for submitting your proposal '{proposal.title}'. "
                    f"After careful review, we were unable to approve it this cycle. "
                    f"You are now eligible to submit preferences for other Innovation projects.\n\n"
                    f"— NU Launch Labs"
                ),
            )
        except smtplib.SMTPException:
            logger.error(
                "Failed to send rejection email for proposal %d to %s",
                proposal.id,
                proposal.proposer.email,
            )

        return proposal

    # ══════════════════════════════════════════════
    # Innovation Projects (approved proposals)
    # ══════════════════════════════════════════════

    @staticmethod
    def list_projects_for_active_cycle():
        """List all approved Innovation projects for the current cycle."""
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        return (
            InnovationProject.objects.filter(cycle=cycle)
            .select_related("cycle", "lead", "proposal")
            .order_by("-created_at")
        )

    @staticmethod
    def get_project(*, project_id: int) -> InnovationProject:
        """Get a single Innovation project by ID."""
        try:
            return InnovationProject.objects.select_related(
                "cycle", "lead", "proposal"
            ).get(id=project_id)
        except InnovationProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Innovation project with id {project_id} not found."
            )

    # ══════════════════════════════════════════════
    # Preferences
    # ══════════════════════════════════════════════

    @staticmethod
    @transaction.atomic
    def submit_preferences(
        *,
        user: User,
        preferences: list[dict],
        ip_address: str = None,
    ) -> list[InnovationPreference]:
        """
        Student submits ranked preferences (up to 3 Innovation projects).

        Input format: [{"project_id": 5, "rank": 1}, ...]

        Business rules:
            - innovation_open must be True
            - GI must be complete (enforced at view level)
            - Student must NOT be already assigned this cycle
            - Student must NOT have a pending (SUBMITTED) or approved proposal
              (rejected proposal is OK — they rejoin the pool)
            - Max 3 preferences, unique ranks (1, 2, 3), unique projects
            - Projects must exist and belong to the current cycle
            - Replaces any existing preferences (upsert pattern)
        """
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        if not cycle.innovation_open:
            raise BusinessLogicError(
                "Innovation applications are not currently open."
            )

        # Check assignment
        if Assignment.objects.filter(user=user, cycle=cycle).exists():
            raise BusinessLogicError(
                "You are already assigned to a project this cycle. "
                "You cannot submit preferences."
            )

        # Check proposal status — block if SUBMITTED or APPROVED
        active_proposal = Proposals.objects.filter(
            proposer=user,
            cycle=cycle,
            status__in=[ProposalStatus.SUBMITTED, ProposalStatus.APPROVED],
        ).first()

        if active_proposal:
            if active_proposal.status == ProposalStatus.SUBMITTED:
                raise BusinessLogicError(
                    "You have a pending proposal under review. "
                    "You cannot submit preferences until it is resolved."
                )
            else:
                raise BusinessLogicError(
                    "Your proposal has been approved. As the project lead, "
                    "you cannot submit preferences for other projects."
                )

        # Validate preference list
        if not preferences:
            raise BusinessLogicError("At least one preference is required.")
        if len(preferences) > 3:
            raise BusinessLogicError("Maximum 3 preferences allowed.")

        # Validate unique ranks and projects
        ranks_seen = set()
        projects_seen = set()
        validated = []

        for pref in preferences:
            rank = pref.get("rank")
            project_id = pref.get("project_id")

            if rank not in (1, 2, 3):
                raise BusinessLogicError(
                    f"Invalid rank: {rank}. Must be 1, 2, or 3."
                )
            if rank in ranks_seen:
                raise BusinessLogicError(
                    f"Duplicate rank: {rank}. Each rank must be unique."
                )
            if project_id in projects_seen:
                raise BusinessLogicError(
                    f"Duplicate project_id: {project_id}. "
                    f"Each project can only be ranked once."
                )

            ranks_seen.add(rank)
            projects_seen.add(project_id)

            # Validate project exists in current cycle
            try:
                project = InnovationProject.objects.get(
                    id=project_id, cycle=cycle
                )
            except InnovationProject.DoesNotExist:
                raise ResourceNotFoundError(
                    f"Innovation project with id {project_id} not found "
                    f"in the current cycle."
                )

            validated.append({"project": project, "rank": rank})

        # Delete existing preferences (upsert pattern)
        InnovationPreference.objects.filter(user=user, cycle=cycle).delete()

        # Create new preferences
        created = []
        for item in validated:
            pref = InnovationPreference.objects.create(
                user=user,
                project=item["project"],
                cycle=cycle,
                rank=item["rank"],
            )
            created.append(pref)

        logger.info(
            "Preferences submitted: %s ranked %d projects (cycle=%s)",
            user.email,
            len(created),
            cycle.name,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="PREFERENCES_SUBMITTED",
            actor=user,
            target_type="InnovationPreference",
            target_id=None,
            metadata={
                "cycle": cycle.name,
                "rankings": [
                    {"project_id": p.project_id, "rank": p.rank}
                    for p in created
                ],
            },
            ip_address=ip_address,
        )

        return created

    @staticmethod
    def get_student_preferences(*, user: User):
        """Get this student's preferences for the current cycle."""
        from apps.cycles.services import CycleService

        try:
            cycle = CycleService.get_current_cycle()
        except ResourceNotFoundError:
            return InnovationPreference.objects.none()

        return (
            InnovationPreference.objects.filter(user=user, cycle=cycle)
            .select_related("project")
            .order_by("rank")
        )

    @staticmethod
    def get_preferences_for_project(*, project_id: int):
        """
        Admin/Ops view: who ranked this project and at what rank.
        Returns preferences grouped by project, useful for assignment decisions.
        """
        try:
            project = InnovationProject.objects.get(id=project_id)
        except InnovationProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Innovation project with id {project_id} not found."
            )

        return (
            InnovationPreference.objects.filter(project=project)
            .select_related("user", "project")
            .order_by("rank")
        )

    # ══════════════════════════════════════════════
    # Assignment (Admin/Ops)
    # ══════════════════════════════════════════════

    @staticmethod
    @transaction.atomic
    def assign_to_project(
        *,
        user_id: int,
        project_id: int,
        assigned_by: User,
        ip_address: str = None,
    ) -> Assignment:
        """
        Admin/Ops assigns a student to an Innovation project.

        Business rules:
            - Student must exist and be a USER role
            - Project must exist in the current cycle
            - Student must NOT already be assigned this cycle
            - Creates an Assignment row (track=INNOVATION)
            - Not gated by innovation_open toggle (admin can assign anytime)
        """
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        # Validate student
        try:
            student = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundError(
                f"User with id {user_id} not found."
            )

        if student.role != User.Role.USER:
            raise BusinessLogicError(
                f"User {student.email} is not a student. "
                f"Only students can be assigned to Innovation projects."
            )

        # Validate project
        try:
            project = InnovationProject.objects.get(
                id=project_id, cycle=cycle
            )
        except InnovationProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Innovation project with id {project_id} not found "
                f"in the current cycle."
            )

        # Check existing assignment
        existing = Assignment.objects.filter(
            user=student, cycle=cycle
        ).first()

        if existing:
            raise ConflictError(
                f"{student.email} is already assigned to a "
                f"{existing.get_track_display()} project this cycle."
            )

        # Check team capacity
        current_members = Assignment.objects.filter(
            innovation_project=project, cycle=cycle
        ).count()
        if current_members >= project.max_members:
            raise BusinessLogicError(
                f"Project '{project.title}' is full "
                f"({current_members}/{project.max_members} members)."
            )

        assignment = Assignment.objects.create(
            user=student,
            cycle=cycle,
            track=Assignment.Track.INNOVATION,
            launch_project=None,
            innovation_project=project,
            assigned_by=assigned_by,
        )

        logger.info(
            "Innovation assignment: %s → '%s' (cycle=%s) by %s",
            student.email,
            project.title,
            cycle.name,
            assigned_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="INNOVATION_ASSIGNED",
            actor=assigned_by,
            target_type="Assignment",
            target_id=assignment.id,
            metadata={
                "student_email": student.email,
                "project_title": project.title,
                "project_id": project.id,
                "cycle": cycle.name,
            },
            ip_address=ip_address,
        )

        try:
            send_notification_email(
                subject="You've been assigned to an Innovation project!",
                recipient_email=student.email,
                plain_message=(
                    f"Hi {student.first_name},\n\n"
                    f"You've been assigned to the Innovation project '{project.title}' "
                    f"for the {cycle.name} cycle.\n\n"
                    f"— NU Launch Labs"
                ),
            )
        except smtplib.SMTPException:
            logger.error(
                "Failed to send assignment email to %s for project '%s'",
                student.email,
                project.title,
            )

        return assignment