"""
Phase 2 tests — Application Cycle management with independent toggles.

Covers: cycle creation, toggle updates, cycle closing, stats, permissions,
toggle independence, audit logging.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cycles.models import ApplicationCycle


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
def active_cycle(db):
    """Create an active cycle with both toggles off."""
    return ApplicationCycle.objects.create(
        name="Fall 2026",
        is_active=True,
        launch_open=False,
        innovation_open=False,
    )


# Cycle Creation Tests

@pytest.mark.django_db
class TestCycleCreation:

    def test_admin_creates_cycle(self, admin_client):
        """Admin can create a new application cycle."""
        resp = admin_client.post(
            reverse("cycles:create"),
            {"name": "Fall 2026", "description": "Test cycle"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["cycle"]["name"] == "Fall 2026"
        assert resp.data["cycle"]["is_active"] is True
        assert resp.data["cycle"]["launch_open"] is False
        assert resp.data["cycle"]["innovation_open"] is False

    def test_cannot_create_duplicate_name(self, admin_client, active_cycle):
        """Duplicate cycle name is rejected."""
        resp = admin_client.post(
            reverse("cycles:create"),
            {"name": "Fall 2026"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_create_when_active_exists(self, admin_client, active_cycle):
        """Cannot create a new cycle when one is already active."""
        resp = admin_client.post(
            reverse("cycles:create"),
            {"name": "Spring 2027"},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_student_cannot_create_cycle(self, student_client):
        """Students cannot create cycles."""
        resp = student_client.post(
            reverse("cycles:create"),
            {"name": "Fall 2026"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ops_chair_cannot_create_cycle(self, ops_client):
        """Ops Chair cannot create cycles."""
        resp = ops_client.post(
            reverse("cycles:create"),
            {"name": "Fall 2026"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_create_cycle(self, api_client):
        """Unauthenticated user cannot create cycles."""
        resp = api_client.post(
            reverse("cycles:create"),
            {"name": "Fall 2026"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# Toggle Update Tests

@pytest.mark.django_db
class TestToggleUpdates:

    def test_open_launch_only(self, admin_client, active_cycle):
        """Admin can open Launch while Innovation stays closed."""
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cycle"]["launch_open"] is True
        assert resp.data["cycle"]["innovation_open"] is False

    def test_open_innovation_only(self, admin_client, active_cycle):
        """Admin can open Innovation while Launch stays closed."""
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"innovation_open": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cycle"]["launch_open"] is False
        assert resp.data["cycle"]["innovation_open"] is True

    def test_open_both_simultaneously(self, admin_client, active_cycle):
        """Admin can open both tracks at the same time."""
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True, "innovation_open": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cycle"]["launch_open"] is True
        assert resp.data["cycle"]["innovation_open"] is True

    def test_close_one_keep_other_open(self, admin_client, active_cycle):
        """Closing one toggle does not affect the other."""
        # Open both
        admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True, "innovation_open": True},
            format="json",
        )
        # Close only Launch
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cycle"]["launch_open"] is False
        assert resp.data["cycle"]["innovation_open"] is True

    def test_toggle_on_then_off_then_on(self, admin_client, active_cycle):
        """Toggles can be flipped back and forth freely."""
        url = reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id})

        # Open
        admin_client.patch(url, {"launch_open": True})
        # Close
        admin_client.patch(url, {"launch_open": False})
        # Reopen
        resp = admin_client.patch(url, {"launch_open": True})

        assert resp.data["cycle"]["launch_open"] is True

    def test_no_change_when_same_value(self, admin_client, active_cycle):
        """Sending the same value doesn't error — it's a no-op."""
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": False},  # already False
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_empty_body_rejected(self, admin_client, active_cycle):
        """Must provide at least one toggle."""
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_toggle_inactive_cycle(self, admin_client, active_cycle):
        """Cannot update toggles on a closed cycle."""
        active_cycle.is_active = False
        active_cycle.save()

        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_student_cannot_toggle(self, student_client, active_cycle):
        """Students cannot update toggles."""
        resp = student_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_toggle_nonexistent_cycle(self, admin_client):
        """404 for nonexistent cycle."""
        resp = admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": 999}),
            {"launch_open": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# Close Cycle Tests

@pytest.mark.django_db
class TestCloseCycle:

    def test_admin_closes_cycle(self, admin_client, active_cycle):
        """Admin can close a cycle."""
        # Open some toggles first
        admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True, "innovation_open": True},
            format="json",
        )

        resp = admin_client.post(
            reverse("cycles:close", kwargs={"cycle_id": active_cycle.id}),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cycle"]["is_active"] is False
        assert resp.data["cycle"]["launch_open"] is False
        assert resp.data["cycle"]["innovation_open"] is False

    def test_cannot_close_already_closed(self, admin_client, active_cycle):
        """Cannot close a cycle that's already closed."""
        admin_client.post(
            reverse("cycles:close", kwargs={"cycle_id": active_cycle.id}),
        )
        resp = admin_client.post(
            reverse("cycles:close", kwargs={"cycle_id": active_cycle.id}),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_can_create_new_cycle_after_closing(self, admin_client, active_cycle):
        """After closing, a new cycle can be created."""
        admin_client.post(
            reverse("cycles:close", kwargs={"cycle_id": active_cycle.id}),
        )
        resp = admin_client.post(
            reverse("cycles:create"),
            {"name": "Spring 2027"},
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_student_cannot_close_cycle(self, student_client, active_cycle):
        """Students cannot close cycles."""
        resp = student_client.post(
            reverse("cycles:close", kwargs={"cycle_id": active_cycle.id}),
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# Current Cycle Tests

@pytest.mark.django_db
class TestCurrentCycle:

    def test_get_current_cycle(self, admin_client, active_cycle):
        """Authenticated user can view current cycle."""
        resp = admin_client.get(reverse("cycles:current"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "Fall 2026"

    def test_student_can_view_current_cycle(self, student_client, active_cycle):
        """Students can view current cycle."""
        resp = student_client.get(reverse("cycles:current"))
        assert resp.status_code == status.HTTP_200_OK

    def test_no_active_cycle(self, admin_client):
        """404 when no active cycle exists."""
        resp = admin_client.get(reverse("cycles:current"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_view_cycle(self, api_client, active_cycle):
        """Unauthenticated user cannot view current cycle."""
        resp = api_client.get(reverse("cycles:current"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# Cycle Stats Tests

@pytest.mark.django_db
class TestCycleStats:

    def test_admin_views_stats(self, admin_client, active_cycle):
        """Admin can view cycle stats."""
        resp = admin_client.get(
            reverse("cycles:stats", kwargs={"cycle_id": active_cycle.id}),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cycle_name"] == "Fall 2026"
        assert "gi_completed" in resp.data
        assert "launch_open" in resp.data
        assert "innovation_open" in resp.data

    def test_ops_views_stats(self, ops_client, active_cycle):
        """Ops Chair can view cycle stats."""
        resp = ops_client.get(
            reverse("cycles:stats", kwargs={"cycle_id": active_cycle.id}),
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_student_cannot_view_stats(self, student_client, active_cycle):
        """Students cannot view cycle stats."""
        resp = student_client.get(
            reverse("cycles:stats", kwargs={"cycle_id": active_cycle.id}),
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# Cycle List Tests

@pytest.mark.django_db
class TestCycleList:

    def test_admin_lists_cycles(self, admin_client, active_cycle):
        """Admin can list all cycles."""
        resp = admin_client.get(reverse("cycles:list"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_filter_by_active(self, admin_client, active_cycle):
        """Can filter cycles by is_active."""
        resp = admin_client.get(
            reverse("cycles:list"), {"is_active": "true"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert all(c["is_active"] for c in resp.data)

    def test_student_cannot_list_cycles(self, student_client, active_cycle):
        """Students cannot list all cycles."""
        resp = student_client.get(reverse("cycles:list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# Audit Integration Tests

@pytest.mark.django_db
class TestCycleAuditLogging:

    def test_cycle_creation_audit(self, admin_client):
        """Creating a cycle generates an audit log entry."""
        from apps.audit.models import AuditLog

        admin_client.post(
            reverse("cycles:create"),
            {"name": "Fall 2026"},
        )

        logs = AuditLog.objects.filter(action="CYCLE_CREATED")
        assert logs.count() == 1
        assert logs.first().metadata["cycle_name"] == "Fall 2026"

    def test_toggle_update_audit(self, admin_client, active_cycle):
        """Toggling creates an audit log with change details."""
        from apps.audit.models import AuditLog

        admin_client.patch(
            reverse("cycles:update-toggles", kwargs={"cycle_id": active_cycle.id}),
            {"launch_open": True},
            format="json",
        )

        logs = AuditLog.objects.filter(action="CYCLE_TOGGLES_UPDATED")
        assert logs.count() == 1
        changes = logs.first().metadata["changes"]
        assert changes["launch_open"]["old"] is False
        assert changes["launch_open"]["new"] is True

    def test_close_cycle_audit(self, admin_client, active_cycle):
        """Closing a cycle generates an audit log."""
        from apps.audit.models import AuditLog

        admin_client.post(
            reverse("cycles:close", kwargs={"cycle_id": active_cycle.id}),
        )

        logs = AuditLog.objects.filter(action="CYCLE_CLOSED")
        assert logs.count() == 1


# Model Tests

@pytest.mark.django_db
class TestCycleModel:

    def test_str_both_closed(self, active_cycle):
        """String representation when both toggles off."""
        assert "All Closed" in str(active_cycle)

    def test_str_launch_open(self, active_cycle):
        """String representation when Launch is open."""
        active_cycle.launch_open = True
        active_cycle.save()
        assert "Launch Open" in str(active_cycle)

    def test_str_both_open(self, active_cycle):
        """String representation when both open."""
        active_cycle.launch_open = True
        active_cycle.innovation_open = True
        active_cycle.save()
        result = str(active_cycle)
        assert "Launch Open" in result
        assert "Innovation Open" in result

    def test_str_inactive(self, active_cycle):
        """String representation shows inactive status."""
        active_cycle.is_active = False
        active_cycle.save()
        assert "Inactive" in str(active_cycle)