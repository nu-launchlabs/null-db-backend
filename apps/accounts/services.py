"""
Account service layer — ALL business logic lives here.


Rules:
    - Views call services, never touch ORM directly.
    - Services raise BusinessLogicError / ConflictError for rule violations.
"""

import logging

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.validators import is_neu_email, validate_neu_email
from utils.exceptions import BusinessLogicError, ConflictError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class AccountService:
    """
    Handles user registration, Launch Team creation, profile updates, role management.
    """

    # Registration
    @staticmethod
    @transaction.atomic
    def register_user(*, email: str, password: str, first_name: str, last_name: str) -> User:
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
        # TODO : AuditService.log(action="USER_REGISTERED", actor=user, ...)
        # TODO : NotificationService.send_welcome(user)

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
            "Launch Team account created: %s (by %s)",
            user.email,
            created_by.email,
        )
        # TODO : AuditService.log(action="LAUNCH_TEAM_CREATED", ...)
        # TODO : NotificationService.send_launch_team_welcome(user)

        return user

    # Profile Management
    @staticmethod
    def update_profile(*, user: User, first_name: str = None, last_name: str = None) -> User:
        """
        Update user's own profile. Only name fields are editable.
        """
        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()
        user.save(update_fields=["first_name", "last_name", "updated_at"])
        return user

    @staticmethod
    def change_password(*, user: User, current_password: str, new_password: str) -> None:
        """
        Change user's password. Validates current password first.
        """
        if not user.check_password(current_password):
            raise BusinessLogicError("Current password is incorrect.")

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("Password changed for user: %s", user.email)

    # Role Management (Admin Only)
    @staticmethod
    @transaction.atomic
    def change_role(*, user_id: int, new_role: str, changed_by: User) -> User:
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
        # TODO : AuditService.log(action="ROLE_CHANGED", ...)

        return user

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