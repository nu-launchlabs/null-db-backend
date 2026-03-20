"""
Launch Track service layer — ALL business logic lives here.

Workflow:
    1. Admin creates LaunchProject (linked to a LAUNCH_TEAM user + active cycle)
    2. Students apply (must have GI done, launch_open=True, no duplicate)
    3. Admin/Ops filter applications → status becomes FILTERED
    4. Admin/Ops send filtered apps to Launch Team → LaunchCandidate created,
       status becomes SENT_TO_TEAM
    5. Launch Team selects candidate → auto-creates Assignment row,
       candidate status = SELECTED, app status = SELECTED
    6. Launch Team rejects candidate → candidate status = REJECTED,
       app status = NOT_SELECTED

Rules:
    - Views call services, never touch ORM directly.
    - Services raise BusinessLogicError / ConflictError for rule violations.
    - Services call AuditService.log() for every significant action.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.cycles.models import Assignment
from apps.launch.models import LaunchApplication, LaunchCandidate, LaunchProject
from utils.exceptions import (
    BusinessLogicError,
    ConflictError,
    ForbiddenError,
    ResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class LaunchService:
    """Handles all Launch Track operations."""

    # ══════════════════════════════════════════════
    # Project Management (Admin)
    # ══════════════════════════════════════════════

    @staticmethod
    @transaction.atomic
    def create_project(
        *,
        team_id: int,
        title: str,
        description: str,
        requirements: str = "",
        max_members: int = 4,
        created_by: User,
        ip_address: str = None,
    ) -> LaunchProject:
        """
        Create a new Launch Project for the current active cycle.

        Business rules:
            - Must have an active cycle
            - team_id must reference a LAUNCH_TEAM user
            - Admin creates projects (enforced at view level)
        """
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        # Validate team user exists and is LAUNCH_TEAM
        try:
            team_user = User.objects.get(id=team_id)
        except User.DoesNotExist:
            raise ResourceNotFoundError(f"User with id {team_id} not found.")

        if team_user.role != User.Role.LAUNCH_TEAM:
            raise BusinessLogicError(
                f"User {team_user.email} is not a Launch Team member. "
                f"Only LAUNCH_TEAM users can own projects."
            )

        project = LaunchProject.objects.create(
            cycle=cycle,
            team=team_user,
            title=title,
            description=description,
            requirements=requirements,
            max_members=max_members,
        )

        logger.info(
            "Launch project created: '%s' (team=%s, cycle=%s) by %s",
            title,
            team_user.email,
            cycle.name,
            created_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="LAUNCH_PROJECT_CREATED",
            actor=created_by,
            target_type="LaunchProject",
            target_id=project.id,
            metadata={
                "title": title,
                "team_email": team_user.email,
                "cycle": cycle.name,
            },
            ip_address=ip_address,
        )

        return project

    @staticmethod
    @transaction.atomic
    def delete_project(
        *, project_id: int, deleted_by: User, ip_address: str = None
    ) -> None:
        """
        Delete a Launch Project. Only if no SELECTED candidates exist.

        Business rules:
            - Cannot delete if any candidate is SELECTED (assignment exists)
            - Admin only (enforced at view level)
        """
        try:
            project = LaunchProject.objects.get(id=project_id)
        except LaunchProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Launch project with id {project_id} not found."
            )

        # Check for existing selections
        has_selections = LaunchCandidate.objects.filter(
            project=project,
            status=LaunchCandidate.Status.SELECTED,
        ).exists()

        if has_selections:
            raise BusinessLogicError(
                "Cannot delete project with selected candidates. "
                "Remove assignments first."
            )

        title = project.title
        cycle_name = project.cycle.name
        project.delete()

        logger.info(
            "Launch project deleted: '%s' (cycle=%s) by %s",
            title,
            cycle_name,
            deleted_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="LAUNCH_PROJECT_DELETED",
            actor=deleted_by,
            target_type="LaunchProject",
            target_id=project_id,
            metadata={"title": title, "cycle": cycle_name},
            ip_address=ip_address,
        )

    @staticmethod
    def get_project(*, project_id: int) -> LaunchProject:
        """Get a single project by ID."""
        try:
            return LaunchProject.objects.select_related(
                "cycle", "team"
            ).get(id=project_id)
        except LaunchProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Launch project with id {project_id} not found."
            )

    @staticmethod
    def list_projects_for_active_cycle():
        """List all projects for the current active cycle."""
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()
        return (
            LaunchProject.objects.filter(cycle=cycle)
            .select_related("cycle", "team")
            .prefetch_related("launch_applications")
        )

    # ══════════════════════════════════════════════
    # Student Application
    # ══════════════════════════════════════════════

    @staticmethod
    @transaction.atomic
    def apply_to_project(
        *,
        user: User,
        project_id: int,
        resume: str = "",
        portfolio: str = "",
        responses: dict = None,
        ip_address: str = None,
    ) -> LaunchApplication:
        """
        Student applies to a Launch Project.

        Business rules:
            - launch_open must be True on the active cycle
            - Student must have completed GI (enforced at view level via IsGIComplete)
            - No duplicate application to the same project in the same cycle
            - Student must not already be assigned this cycle
        """
        from apps.cycles.services import CycleService

        cycle = CycleService.get_current_cycle()

        if not cycle.launch_open:
            raise BusinessLogicError(
                "Launch applications are not currently open."
            )

        # Get the project (must belong to this cycle)
        try:
            project = LaunchProject.objects.get(id=project_id, cycle=cycle)
        except LaunchProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Launch project with id {project_id} not found "
                f"in the current cycle."
            )

        # Check for duplicate application
        if LaunchApplication.objects.filter(
            user=user, project=project, cycle=cycle
        ).exists():
            raise ConflictError(
                "You have already applied to this project."
            )

        # Check if already assigned this cycle
        if Assignment.objects.filter(user=user, cycle=cycle).exists():
            raise BusinessLogicError(
                "You are already assigned to a project this cycle. "
                "You cannot apply to more projects."
            )

        application = LaunchApplication.objects.create(
            user=user,
            project=project,
            cycle=cycle,
            resume=resume or "",
            portfolio=portfolio or "",
            responses=responses or {},
            status=LaunchApplication.Status.SUBMITTED,
        )

        logger.info(
            "Launch application submitted: %s → '%s' (cycle=%s)",
            user.email,
            project.title,
            cycle.name,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="LAUNCH_APPLICATION_SUBMITTED",
            actor=user,
            target_type="LaunchApplication",
            target_id=application.id,
            metadata={
                "project_title": project.title,
                "project_id": project.id,
                "cycle": cycle.name,
            },
            ip_address=ip_address,
        )

        return application

    @staticmethod
    def get_student_applications(*, user: User):
        """Get all Launch applications for the current cycle for this student."""
        from apps.cycles.services import CycleService

        try:
            cycle = CycleService.get_current_cycle()
        except ResourceNotFoundError:
            return LaunchApplication.objects.none()

        return (
            LaunchApplication.objects.filter(user=user, cycle=cycle)
            .select_related("project")
            .order_by("-created_at")
        )

    # ══════════════════════════════════════════════
    # Admin/Ops: View & Filter Applicants
    # ══════════════════════════════════════════════

    @staticmethod
    def get_applicants_for_project(*, project_id: int, status_filter: str = None):
        """
        Get all applications for a specific project.
        Optionally filter by status.
        """
        try:
            project = LaunchProject.objects.get(id=project_id)
        except LaunchProject.DoesNotExist:
            raise ResourceNotFoundError(
                f"Launch project with id {project_id} not found."
            )

        qs = (
            LaunchApplication.objects.filter(project=project)
            .select_related("user", "project")
            .order_by("-created_at")
        )

        if status_filter:
            status_upper = status_filter.upper()
            valid = [s.value for s in LaunchApplication.Status]
            if status_upper not in valid:
                raise BusinessLogicError(
                    f"Invalid status filter: {status_filter}. "
                    f"Valid values: {', '.join(valid)}"
                )
            qs = qs.filter(status=status_upper)

        return qs

    @staticmethod
    @transaction.atomic
    def filter_applications(
        *,
        application_ids: list[int],
        filtered_by: User,
        ip_address: str = None,
    ) -> list[LaunchApplication]:
        """
        Mark applications as FILTERED. Only SUBMITTED apps can be filtered.

        Business rules:
            - Application must exist and be in SUBMITTED status
            - Admin/Ops Chair only (enforced at view level)
        """
        applications = LaunchApplication.objects.filter(
            id__in=application_ids
        ).select_related("user", "project")

        found_ids = set(applications.values_list("id", flat=True))
        missing = set(application_ids) - found_ids
        if missing:
            raise ResourceNotFoundError(
                f"Applications not found: {sorted(missing)}"
            )

        # Validate all are in SUBMITTED status
        invalid = [
            a for a in applications
            if a.status != LaunchApplication.Status.SUBMITTED
        ]
        if invalid:
            invalid_info = [
                f"#{a.id} ({a.get_status_display()})" for a in invalid
            ]
            raise BusinessLogicError(
                f"Only SUBMITTED applications can be filtered. "
                f"Invalid: {', '.join(invalid_info)}"
            )

        updated = []
        from apps.audit.services import AuditService

        for app in applications:
            app.status = LaunchApplication.Status.FILTERED
            app.save(update_fields=["status", "updated_at"])
            updated.append(app)

            AuditService.log(
                action="LAUNCH_APPLICATION_FILTERED",
                actor=filtered_by,
                target_type="LaunchApplication",
                target_id=app.id,
                metadata={
                    "applicant_email": app.user.email,
                    "project_title": app.project.title,
                },
                ip_address=ip_address,
            )

        logger.info(
            "%d applications filtered by %s",
            len(updated),
            filtered_by.email,
        )

        return updated

    @staticmethod
    @transaction.atomic
    def send_to_team(
        *,
        application_ids: list[int],
        sent_by: User,
        ip_address: str = None,
    ) -> list[LaunchCandidate]:
        """
        Send filtered applications to the Launch Team for review.
        Creates LaunchCandidate records and updates app status to SENT_TO_TEAM.

        Business rules:
            - Application must be in FILTERED status
            - Cannot send an application that already has a candidate record
            - Admin/Ops only (enforced at view level)
        """
        applications = LaunchApplication.objects.filter(
            id__in=application_ids
        ).select_related("user", "project", "cycle")

        found_ids = set(applications.values_list("id", flat=True))
        missing = set(application_ids) - found_ids
        if missing:
            raise ResourceNotFoundError(
                f"Applications not found: {sorted(missing)}"
            )

        invalid = [
            a for a in applications
            if a.status != LaunchApplication.Status.FILTERED
        ]
        if invalid:
            invalid_info = [
                f"#{a.id} ({a.get_status_display()})" for a in invalid
            ]
            raise BusinessLogicError(
                f"Only FILTERED applications can be sent to team. "
                f"Invalid: {', '.join(invalid_info)}"
            )

        # Check for existing candidate records
        existing_candidates = set(
            LaunchCandidate.objects.filter(
                application_id__in=application_ids
            ).values_list("application_id", flat=True)
        )
        already_sent = set(application_ids) & existing_candidates
        if already_sent:
            raise ConflictError(
                f"Applications already sent to team: {sorted(already_sent)}"
            )

        candidates = []
        from apps.audit.services import AuditService

        for app in applications:
            # Update application status
            app.status = LaunchApplication.Status.SENT_TO_TEAM
            app.save(update_fields=["status", "updated_at"])

            # Create candidate record for Launch Team review
            candidate = LaunchCandidate.objects.create(
                application=app,
                project=app.project,
                status=LaunchCandidate.Status.PENDING_REVIEW,
            )
            candidates.append(candidate)

            AuditService.log(
                action="LAUNCH_SENT_TO_TEAM",
                actor=sent_by,
                target_type="LaunchCandidate",
                target_id=candidate.id,
                metadata={
                    "applicant_email": app.user.email,
                    "project_title": app.project.title,
                    "application_id": app.id,
                },
                ip_address=ip_address,
            )

        logger.info(
            "%d applications sent to team by %s",
            len(candidates),
            sent_by.email,
        )

        return candidates

    # ══════════════════════════════════════════════
    # Launch Team: View & Select Candidates
    # ══════════════════════════════════════════════

    @staticmethod
    def get_candidates_for_team(*, team_user: User):
        """
        Get all candidates sent to this Launch Team member's projects.
        Only returns candidates for projects owned by this team user.
        """
        from apps.cycles.services import CycleService

        try:
            cycle = CycleService.get_current_cycle()
        except ResourceNotFoundError:
            return LaunchCandidate.objects.none()

        return (
            LaunchCandidate.objects.filter(
                project__team=team_user,
                project__cycle=cycle,
            )
            .select_related(
                "application__user",
                "application__cycle",
                "project",
            )
            .order_by("project__title", "-created_at")
        )

    @staticmethod
    @transaction.atomic
    def select_candidate(
        *,
        candidate_id: int,
        selected_by: User,
        ip_address: str = None,
    ) -> tuple:
        """
        Launch Team selects a candidate → auto-creates Assignment.

        Returns:
            tuple: (LaunchCandidate, Assignment, warning_message or None)

        Business rules:
            - Candidate must be PENDING_REVIEW
            - Launch Team can only select candidates for their own projects
            - If user already has an assignment (Innovation), return warning
              but still allow the selection (admin resolves later)
            - Creates an Assignment row (track=LAUNCH)
            - Updates candidate status to SELECTED
            - Updates application status to SELECTED
        """
        try:
            candidate = LaunchCandidate.objects.select_related(
                "application__user",
                "application__cycle",
                "project__team",
                "project__cycle",
            ).get(id=candidate_id)
        except LaunchCandidate.DoesNotExist:
            raise ResourceNotFoundError(
                f"Candidate with id {candidate_id} not found."
            )

        # Verify Launch Team owns this project
        if candidate.project.team_id != selected_by.id:
            raise ForbiddenError(
                "You can only select candidates for your own projects."
            )

        if candidate.status != LaunchCandidate.Status.PENDING_REVIEW:
            raise BusinessLogicError(
                f"Candidate is already {candidate.get_status_display()}. "
                f"Only PENDING_REVIEW candidates can be selected."
            )

        applicant = candidate.application.user
        cycle = candidate.application.cycle
        warning = None

        # Check for existing assignment (conflict detection)
        existing_assignment = Assignment.objects.filter(
            user=applicant, cycle=cycle
        ).first()

        if existing_assignment:
            if existing_assignment.track == Assignment.Track.LAUNCH:
                raise ConflictError(
                    f"{applicant.email} is already assigned to a Launch project "
                    f"this cycle."
                )
            else:
                # Innovation assignment exists — warn but proceed
                # Launch takes priority per business rules
                warning = (
                    f"WARNING: {applicant.email} currently has an Innovation "
                    f"assignment. This Launch selection will require admin "
                    f"to resolve the conflict."
                )
                logger.warning(
                    "Conflict: %s selected for Launch but has Innovation "
                    "assignment in cycle %s",
                    applicant.email,
                    cycle.name,
                )

        # If no existing Launch assignment, create one
        if not existing_assignment or existing_assignment.track != Assignment.Track.LAUNCH:
            if existing_assignment:
                # Replace Innovation assignment with Launch (Launch priority)
                existing_assignment.delete()

            assignment = Assignment.objects.create(
                user=applicant,
                cycle=cycle,
                track=Assignment.Track.LAUNCH,
                launch_project=candidate.project,
                innovation_project_id_placeholder=None,
                assigned_by=selected_by,
            )
        else:
            # This shouldn't happen (caught above), but safety net
            assignment = existing_assignment

        # Update candidate status
        candidate.status = LaunchCandidate.Status.SELECTED
        candidate.selected_at = timezone.now()
        candidate.save(update_fields=["status", "selected_at", "updated_at"])

        # Update application status
        app = candidate.application
        app.status = LaunchApplication.Status.SELECTED
        app.save(update_fields=["status", "updated_at"])

        logger.info(
            "Candidate selected: %s → '%s' (cycle=%s) by %s",
            applicant.email,
            candidate.project.title,
            cycle.name,
            selected_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="LAUNCH_CANDIDATE_SELECTED",
            actor=selected_by,
            target_type="LaunchCandidate",
            target_id=candidate.id,
            metadata={
                "applicant_email": applicant.email,
                "project_title": candidate.project.title,
                "cycle": cycle.name,
                "had_innovation_assignment": warning is not None,
            },
            ip_address=ip_address,
        )

        return candidate, assignment, warning

    @staticmethod
    @transaction.atomic
    def reject_candidate(
        *,
        candidate_id: int,
        rejected_by: User,
        ip_address: str = None,
    ) -> LaunchCandidate:
        """
        Launch Team rejects a candidate.

        Business rules:
            - Candidate must be PENDING_REVIEW
            - Launch Team can only reject candidates for their own projects
            - Updates candidate status to REJECTED
            - Updates application status to NOT_SELECTED
        """
        try:
            candidate = LaunchCandidate.objects.select_related(
                "application__user",
                "project__team",
            ).get(id=candidate_id)
        except LaunchCandidate.DoesNotExist:
            raise ResourceNotFoundError(
                f"Candidate with id {candidate_id} not found."
            )

        if candidate.project.team_id != rejected_by.id:
            raise ForbiddenError(
                "You can only reject candidates for your own projects."
            )

        if candidate.status != LaunchCandidate.Status.PENDING_REVIEW:
            raise BusinessLogicError(
                f"Candidate is already {candidate.get_status_display()}. "
                f"Only PENDING_REVIEW candidates can be rejected."
            )

        # Update candidate
        candidate.status = LaunchCandidate.Status.REJECTED
        candidate.save(update_fields=["status", "updated_at"])

        # Update application
        app = candidate.application
        app.status = LaunchApplication.Status.NOT_SELECTED
        app.save(update_fields=["status", "updated_at"])

        logger.info(
            "Candidate rejected: %s for '%s' by %s",
            app.user.email,
            candidate.project.title,
            rejected_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="LAUNCH_CANDIDATE_REJECTED",
            actor=rejected_by,
            target_type="LaunchCandidate",
            target_id=candidate.id,
            metadata={
                "applicant_email": app.user.email,
                "project_title": candidate.project.title,
            },
            ip_address=ip_address,
        )

        return candidate    