"""
Audit service — single entry point for all audit logging.

Every service across the platform calls AuditService.log() to record actions.
This is the one service that does NOT call audit logging itself (no recursion).

"""

import logging

from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Centralized audit logging.

    Usage from any service:
        from apps.audit.services import AuditService

        AuditService.log(
            action="USER_REGISTERED",
            actor=user,
            target_type="User",
            target_id=user.id,
            metadata={"email": user.email, "role": user.role},
            ip_address=ip,
        )
    """

    @staticmethod
    def log(
        *,
        action: str,
        actor=None,
        target_type: str = "",
        target_id: int = None,
        metadata: dict = None,
        ip_address: str = None,
    ) -> AuditLog:
        """
        Create an immutable audit log entry.

        Args:
            action: One of AuditLog.Action choices.
            actor: The User who performed the action (None for system actions).
            target_type: Model class name, e.g. "User", "ApplicationCycle".
            target_id: Primary key of the affected record.
            metadata: Dict of action-specific details.
            ip_address: Client IP address.

        Returns:
            The created AuditLog instance.
        """
        if metadata is None:
            metadata = {}

        try:
            entry = AuditLog.objects.create(
                actor=actor,
                action=action,
                target_type=target_type,
                target_id=target_id,
                metadata=metadata,
                ip_address=ip_address,
            )

            logger.info(
                "AUDIT: %s by %s on %s:%s",
                action,
                actor.email if actor else "System",
                target_type,
                target_id,
            )

            return entry

        except Exception as e:
            # Audit logging should NEVER break the main operation.
            # Log the failure and continue.
            logger.error(
                "Failed to create audit log: action=%s, error=%s",
                action,
                str(e),
            )
            return None

    @staticmethod
    def get_logs(
        queryset=None,
        action: str = None,
        actor_id: int = None,
        target_type: str = None,
    ):
        """
        Retrieve audit logs with optional filters.

        Used by admin dashboard to view audit trail.
        """
        qs = queryset if queryset is not None else AuditLog.objects.all()

        if action:
            qs = qs.filter(action=action)
        if actor_id:
            qs = qs.filter(actor_id=actor_id)
        if target_type:
            qs = qs.filter(target_type=target_type)

        return qs.select_related("actor")

    @staticmethod
    def get_ip_from_request(request) -> str:
        """
        Extract client IP from the request.

        Handles X-Forwarded-For header for reverse proxy setups.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")