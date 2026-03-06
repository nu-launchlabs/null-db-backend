"""
Account service layer — ALL business logic lives here.


Rules:
    - Views call services, never touch ORM directly.
    - Services raise BusinessLogicError / ConflictError for rule violations.
    - Services call AuditService.log() for every significant action.
"""

import logging

from django.db import transaction

from apps.accounts.models import GeneralInterest, User
from apps.accounts.validators import is_neu_email, validate_neu_email
from utils.exceptions import BusinessLogicError, ConflictError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class AccountService:
    """
    Handles user registration, Launch Team creation, profile updates,
    role management, and General Interest form submission.
    """

    # Registration
    @staticmethod
    @transaction.atomic
    def register_user(
        *, email: str, password: str, first_name: str, last_name: str,
        ip_address: str = None,
    ) -> User:
        """
        Register a new NEU student user.

        Business rules:
            - Email must be @northeastern.edu or @husky.neu.edu
            - Email must be unique
            - Default role = USER
        """
        email = email.lower().strip()

        # Validate NEU email (service-level check in addition to serializer)
        validate_neu_email(email)

        # Check for existing user (defense-in-depth, serializer also checks)
        if User.objects.filter(email=email).exists():
            raise ConflictError("A user with this email already exists.")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=User.Role.USER,
            is_neu_email=True,
        )

        logger.info("User registered: %s (role=%s)", user.email, user.role)

        from apps.audit.services import AuditService

        AuditService.log(
            action="USER_REGISTERED",
            actor=user,
            target_type="User",
            target_id=user.id,
            metadata={"email": user.email, "role": user.role},
            ip_address=ip_address,
        )

        return user

    # Launch Team Account Creation
    @staticmethod
    @transaction.atomic
    def create_launch_team_account(
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        created_by: User,
        ip_address: str = None,
    ) -> User:
        """
        Admin creates a Launch Team account. Any email domain is allowed.

        Business rules:
            - Only ADMIN can call this (enforced at view level via permissions)
            - LAUNCH_TEAM role is auto-assigned
            - is_neu_email is set based on actual email domain
        """
        email = email.lower().strip()

        if User.objects.filter(email=email).exists():
            raise ConflictError("A user with this email already exists.")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=User.Role.LAUNCH_TEAM,
            is_neu_email=is_neu_email(email),
        )

        logger.info(
            "Launch Team account created: %s by %s",
            user.email,
            created_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="LAUNCH_TEAM_CREATED",
            actor=created_by,
            target_type="User",
            target_id=user.id,
            metadata={
                "email": user.email,
                "created_by": created_by.email,
            },
            ip_address=ip_address,
        )

        return user

    # Profile Management
    @staticmethod
    def update_profile(*, user: User, first_name: str = None, last_name: str = None) -> User:
        """
        Update user's own profile (name fields only).
        """
        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()

        user.save(update_fields=["first_name", "last_name", "updated_at"])
        return user

    @staticmethod
    def change_password(
        *, user: User, current_password: str, new_password: str,
        ip_address: str = None,
    ) -> None:
        """
        Change user's password after verifying current password.
        """
        if not user.check_password(current_password):
            raise BusinessLogicError("Current password is incorrect.")

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        logger.info("Password changed for: %s", user.email)

        from apps.audit.services import AuditService

        AuditService.log(
            action="PASSWORD_CHANGED",
            actor=user,
            target_type="User",
            target_id=user.id,
            metadata={"email": user.email},
            ip_address=ip_address,
        )

    # Role Management
    @staticmethod
    @transaction.atomic
    def change_role(
        *, user_id: int, new_role: str, changed_by: User,
        ip_address: str = None,
    ) -> User:
        """
        Admin changes a user's role.

        Business rules:
            - Cannot change own role (prevent admin from locking themselves out)
            - NEU email required for ADMIN/OPS_CHAIR/USER roles
            - Non-NEU email only valid for LAUNCH_TEAM role
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundError(f"User with id {user_id} not found.")

        if user.id == changed_by.id:
            raise BusinessLogicError("You cannot change your own role.")

        # Validate email-role compatibility
        if new_role in [User.Role.ADMIN, User.Role.OPS_CHAIR, User.Role.USER]:
            if not user.is_neu_email:
                raise BusinessLogicError(
                    f"Cannot assign role {new_role} to a non-Northeastern email. "
                    f"Only LAUNCH_TEAM role is available for non-NEU emails."
                )

        old_role = user.role
        user.role = new_role

        # Sync Django staff permission for Admin role
        user.is_staff = new_role == User.Role.ADMIN
        user.save(update_fields=["role", "is_staff", "updated_at"])

        logger.info(
            "Role changed: %s (%s → %s) by %s",
            user.email,
            old_role,
            new_role,
            changed_by.email,
        )

        from apps.audit.services import AuditService

        AuditService.log(
            action="ROLE_CHANGED",
            actor=changed_by,
            target_type="User",
            target_id=user.id,
            metadata={
                "email": user.email,
                "old_role": old_role,
                "new_role": new_role,
            },
            ip_address=ip_address,
        )

        return user

    # General Interest Form (Phase 2)
    @staticmethod
    @transaction.atomic
    def submit_gi(
        *,
        user: User,
        graduation_year: int,
        college: str,
        major: str,
        skills: str,
        interest_areas: str,
        why_join: str,
        ip_address: str = None,
    ) -> tuple:
        """
        Submit or update General Interest form for the current active cycle.

        If the user has already submitted a GI for the current cycle,
        this updates it instead of rejecting. (Upsert pattern.)

        Business rules:
            - Only USER role can submit
            - Must have an active cycle (any phase)
            - Sets user.is_gi_complete = True on first submission

        Returns:
            tuple: (GeneralInterest instance, bool created)
                   created=True if new, False if updated
        """
        from apps.cycles.services import CycleService

        # Rule: Only students can submit GI
        if user.role != User.Role.USER:
            raise BusinessLogicError(
                "Only students (USER role) can submit the General Interest form."
            )

        # Rule: Must have an active cycle
        cycle = CycleService.get_current_cycle()

        # Upsert: update if exists, create if not
        existing_gi = GeneralInterest.objects.filter(user=user, cycle=cycle).first()

        gi_data = {
            "graduation_year": graduation_year,
            "college": college.strip(),
            "major": major.strip(),
            "skills": skills.strip(),
            "interest_areas": interest_areas.strip(),
            "why_join": why_join.strip(),
        }

        if existing_gi:
            # Update existing GI
            for field, value in gi_data.items():
                setattr(existing_gi, field, value)
            existing_gi.save()
            gi = existing_gi
            created = False

            logger.info(
                "GI updated: %s for cycle '%s'", user.email, cycle.name
            )

            from apps.audit.services import AuditService

            AuditService.log(
                action="GI_UPDATED",
                actor=user,
                target_type="GeneralInterest",
                target_id=gi.id,
                metadata={
                    "email": user.email,
                    "cycle": cycle.name,
                    "graduation_year": graduation_year,
                },
                ip_address=ip_address,
            )
        else:
            # Create new GI
            gi = GeneralInterest.objects.create(
                user=user,
                cycle=cycle,
                **gi_data,
            )
            created = True

            # Mark user as GI complete (only on first submission)
            if not user.is_gi_complete:
                user.is_gi_complete = True
                user.save(update_fields=["is_gi_complete", "updated_at"])

            logger.info(
                "GI submitted: %s for cycle '%s'", user.email, cycle.name
            )

            from apps.audit.services import AuditService

            AuditService.log(
                action="GI_SUBMITTED",
                actor=user,
                target_type="GeneralInterest",
                target_id=gi.id,
                metadata={
                    "email": user.email,
                    "cycle": cycle.name,
                    "graduation_year": graduation_year,
                },
                ip_address=ip_address,
            )

        return gi, created

    @staticmethod
    def get_user_gi(*, user: User):
        """
        Get the user's GI submission for the current active cycle.

        Returns None if no GI submitted yet or no active cycle.
        """
        from apps.cycles.services import CycleService

        try:
            cycle = CycleService.get_current_cycle()
        except ResourceNotFoundError:
            return None

        return GeneralInterest.objects.filter(
            user=user, cycle=cycle
        ).select_related("cycle").first()

    # Query Helpers
    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """Fetch a single user or raise 404."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundError(f"User with id {user_id} not found.")

    @staticmethod
    def get_all_users(queryset=None):
        """Return all users, optionally from a pre-filtered queryset."""
        if queryset is not None:
            return queryset
        return User.objects.all()