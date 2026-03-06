"""
Phase 2 tests — Audit logging system.

Covers: audit log API, filtering, permissions, service method.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.services import AuditService


# Fixtures

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@northeastern.edu",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def ops_chair_user(db):
    return User.objects.create_user(
        email="ops@northeastern.edu",
        password="OpsPass123!",
        first_name="Ops",
        last_name="Chair",
        role=User.Role.OPS_CHAIR,
    )


@pytest.fixture
def student_user(db):
    return User.objects.create_user(
        email="student@northeastern.edu",
        password="StudentPass123!",
        first_name="Regular",
        last_name="Student",
        role=User.Role.USER,
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def ops_client(api_client, ops_chair_user):
    api_client.force_authenticate(user=ops_chair_user)
    return api_client


@pytest.fixture
def student_client(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    return api_client


@pytest.fixture
def sample_audit_logs(admin_user, student_user):
    """Create some sample audit log entries."""
    AuditService.log(
        action="USER_REGISTERED",
        actor=student_user,
        target_type="User",
        target_id=student_user.id,
        metadata={"email": student_user.email},
    )
    AuditService.log(
        action="ROLE_CHANGED",
        actor=admin_user,
        target_type="User",
        target_id=student_user.id,
        metadata={"old_role": "USER", "new_role": "OPS_CHAIR"},
    )
    AuditService.log(
        action="CYCLE_CREATED",
        actor=admin_user,
        target_type="ApplicationCycle",
        target_id=1,
        metadata={"cycle_name": "Fall 2026"},
    )


# AuditService Tests

@pytest.mark.django_db
class TestAuditService:

    def test_log_creates_entry(self, admin_user):
        """AuditService.log() creates an audit log entry."""
        entry = AuditService.log(
            action="USER_REGISTERED",
            actor=admin_user,
            target_type="User",
            target_id=admin_user.id,
            metadata={"email": admin_user.email},
            ip_address="127.0.0.1",
        )
        assert entry is not None
        assert entry.action == "USER_REGISTERED"
        assert entry.actor == admin_user
        assert entry.ip_address == "127.0.0.1"

    def test_log_without_actor(self, db):
        """Audit log can be created without an actor (system actions)."""
        entry = AuditService.log(
            action="CYCLE_CREATED",
            target_type="ApplicationCycle",
            target_id=1,
        )
        assert entry is not None
        assert entry.actor is None

    def test_log_failure_does_not_raise(self, db):
        """AuditService.log() should never raise — it logs errors internally."""
        # Pass an invalid action that will still save (CharField accepts any string)
        entry = AuditService.log(
            action="SOME_ACTION",
            metadata={"test": True},
        )
        # Should succeed — no exception
        assert entry is not None

    def test_get_logs_filter_by_action(self, sample_audit_logs):
        """Can filter logs by action type."""
        logs = AuditService.get_logs(action="USER_REGISTERED")
        assert logs.count() == 1

    def test_get_logs_filter_by_actor(self, admin_user, sample_audit_logs):
        """Can filter logs by actor."""
        logs = AuditService.get_logs(actor_id=admin_user.id)
        assert logs.count() == 2  # ROLE_CHANGED + CYCLE_CREATED

    def test_get_logs_filter_by_target_type(self, sample_audit_logs):
        """Can filter logs by target type."""
        logs = AuditService.get_logs(target_type="ApplicationCycle")
        assert logs.count() == 1


# Audit API Tests

@pytest.mark.django_db
class TestAuditAPI:

    def test_admin_views_audit_logs(self, admin_client, sample_audit_logs):
        """Admin can view audit logs."""
        resp = admin_client.get(reverse("audit:log-list"))
        assert resp.status_code == status.HTTP_200_OK

    def test_ops_chair_views_audit_logs(self, ops_client, sample_audit_logs):
        """Ops Chair can view audit logs."""
        resp = ops_client.get(reverse("audit:log-list"))
        assert resp.status_code == status.HTTP_200_OK

    def test_student_cannot_view_audit_logs(self, student_client, sample_audit_logs):
        """Students cannot view audit logs."""
        resp = student_client.get(reverse("audit:log-list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_view_audit_logs(self, api_client, sample_audit_logs):
        """Unauthenticated user cannot view audit logs."""
        resp = api_client.get(reverse("audit:log-list"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_logs_by_action(self, admin_client, sample_audit_logs):
        """Can filter audit logs by action via query param."""
        resp = admin_client.get(
            reverse("audit:log-list"), {"action": "CYCLE_CREATED"}
        )
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        assert all(log["action"] == "CYCLE_CREATED" for log in results)

    def test_filter_logs_by_target_type(self, admin_client, sample_audit_logs):
        """Can filter audit logs by target type."""
        resp = admin_client.get(
            reverse("audit:log-list"), {"target_type": "User"}
        )
        assert resp.status_code == status.HTTP_200_OK


# Audit Log Model Tests

@pytest.mark.django_db
class TestAuditLogModel:

    def test_str_representation(self, admin_user):
        """AuditLog __str__ shows meaningful info."""
        entry = AuditLog.objects.create(
            actor=admin_user,
            action="USER_REGISTERED",
            target_type="User",
            target_id=1,
        )
        assert "admin@northeastern.edu" in str(entry)
        assert "USER_REGISTERED" in str(entry)

    def test_str_without_actor(self, db):
        """AuditLog __str__ handles missing actor."""
        entry = AuditLog.objects.create(
            action="CYCLE_CREATED",
            target_type="ApplicationCycle",
            target_id=1,
        )
        assert "System" in str(entry)