"""
Phase 2 tests — General Interest form submission & editing.

Covers: GI submission, GI update (upsert), always-open access,
role checks, GI viewing, audit logging integration.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import GeneralInterest, User
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
def student_user(db):
    return User.objects.create_user(
        email="student@northeastern.edu",
        password="StudentPass123!",
        first_name="Regular",
        last_name="Student",
        role=User.Role.USER,
    )


@pytest.fixture
def launch_team_user(db):
    return User.objects.create_user(
        email="startup@techcompany.com",
        password="LaunchPass123!",
        first_name="Startup",
        last_name="Founder",
        role=User.Role.LAUNCH_TEAM,
        is_neu_email=False,
    )


@pytest.fixture
def student_client(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def launch_client(api_client, launch_team_user):
    api_client.force_authenticate(user=launch_team_user)
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


@pytest.fixture
def cycle_launch_open(db):
    """Create an active cycle with Launch open."""
    return ApplicationCycle.objects.create(
        name="Fall 2026",
        is_active=True,
        launch_open=True,
        innovation_open=False,
    )


@pytest.fixture
def cycle_both_open(db):
    """Create an active cycle with both toggles on."""
    return ApplicationCycle.objects.create(
        name="Fall 2026",
        is_active=True,
        launch_open=True,
        innovation_open=True,
    )


@pytest.fixture
def valid_gi_data():
    """Valid GI form data."""
    return {
        "graduation_year": 2027,
        "college": "Khoury College of Computer Sciences",
        "major": "Computer Science",
        "skills": "Python, Django, React, SQL, Machine Learning",
        "interest_areas": "Engineering, Product Development",
        "why_join": "I want to gain real-world startup experience and build products that matter.",
    }


@pytest.fixture
def updated_gi_data():
    """Updated GI form data."""
    return {
        "graduation_year": 2028,
        "college": "College of Engineering",
        "major": "Data Science",
        "skills": "Python, TensorFlow, Spark, AWS, Kubernetes",
        "interest_areas": "AI/ML, Data Engineering",
        "why_join": "Updated: I want to apply ML to real startup problems.",
    }


# GI Submission Tests

@pytest.mark.django_db
class TestGISubmission:

    def test_student_submits_gi_success(self, student_client, active_cycle, valid_gi_data):
        """Student can submit GI when a cycle is active."""
        resp = student_client.post(
            reverse("accounts:submit-gi"), valid_gi_data
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["general_interest"]["graduation_year"] == 2027
        assert resp.data["general_interest"]["college"] == "Khoury College of Computer Sciences"

    def test_gi_works_with_toggles_off(self, student_client, active_cycle, valid_gi_data):
        """GI can be submitted even when both toggles are off (always open)."""
        resp = student_client.post(
            reverse("accounts:submit-gi"), valid_gi_data
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_gi_works_with_launch_open(self, student_client, cycle_launch_open, valid_gi_data):
        """GI can be submitted when Launch is open."""
        resp = student_client.post(
            reverse("accounts:submit-gi"), valid_gi_data
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_gi_works_with_both_open(self, student_client, cycle_both_open, valid_gi_data):
        """GI can be submitted when both tracks are open."""
        resp = student_client.post(
            reverse("accounts:submit-gi"), valid_gi_data
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_gi_marks_user_complete(self, student_client, student_user, active_cycle, valid_gi_data):
        """GI submission sets user.is_gi_complete = True."""
        assert student_user.is_gi_complete is False

        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)

        student_user.refresh_from_db()
        assert student_user.is_gi_complete is True

    def test_gi_creates_record(self, student_client, student_user, active_cycle, valid_gi_data):
        """GI submission creates a GeneralInterest record in the DB."""
        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)

        gi = GeneralInterest.objects.get(user=student_user, cycle=active_cycle)
        assert gi.major == "Computer Science"
        assert gi.graduation_year == 2027

    def test_gi_rejected_no_active_cycle(self, student_client, valid_gi_data):
        """GI submission is rejected when no active cycle exists."""
        resp = student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_cannot_submit_gi(self, admin_client, active_cycle, valid_gi_data):
        """Admin cannot submit GI (student role required)."""
        resp = admin_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_launch_team_cannot_submit_gi(self, launch_client, active_cycle, valid_gi_data):
        """Launch Team cannot submit GI."""
        resp = launch_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_submit_gi(self, api_client, active_cycle, valid_gi_data):
        """Unauthenticated user cannot submit GI."""
        resp = api_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# GI Update (Upsert) Tests

@pytest.mark.django_db
class TestGIUpdate:

    def test_resubmit_updates_existing_gi(
        self, student_client, active_cycle, valid_gi_data, updated_gi_data
    ):
        """Second submission updates the existing GI instead of creating a duplicate."""
        resp1 = student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp1.status_code == status.HTTP_201_CREATED

        resp2 = student_client.post(reverse("accounts:submit-gi"), updated_gi_data)
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["message"] == "General Interest form updated successfully."
        assert resp2.data["general_interest"]["graduation_year"] == 2028
        assert resp2.data["general_interest"]["major"] == "Data Science"

    def test_update_does_not_create_duplicate(
        self, student_client, student_user, active_cycle, valid_gi_data, updated_gi_data
    ):
        """Updating GI does not create a second record."""
        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        student_client.post(reverse("accounts:submit-gi"), updated_gi_data)

        count = GeneralInterest.objects.filter(
            user=student_user, cycle=active_cycle
        ).count()
        assert count == 1

    def test_update_preserves_gi_complete_flag(
        self, student_client, student_user, active_cycle, valid_gi_data, updated_gi_data
    ):
        """Updating GI keeps is_gi_complete = True."""
        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)

        student_user.refresh_from_db()
        assert student_user.is_gi_complete is True

        student_client.post(reverse("accounts:submit-gi"), updated_gi_data)

        student_user.refresh_from_db()
        assert student_user.is_gi_complete is True

    def test_update_reflects_in_view(
        self, student_client, active_cycle, valid_gi_data, updated_gi_data
    ):
        """Updated GI data is visible via the view endpoint."""
        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        student_client.post(reverse("accounts:submit-gi"), updated_gi_data)

        resp = student_client.get(reverse("accounts:view-gi"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["major"] == "Data Science"
        assert resp.data["graduation_year"] == 2028

    def test_partial_update_replaces_all_fields(
        self, student_client, active_cycle, valid_gi_data
    ):
        """All fields are replaced on update (full form resubmission)."""
        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)

        new_data = {
            "graduation_year": 2029,
            "college": "New College",
            "major": "New Major",
            "skills": "New Skills",
            "interest_areas": "New Areas",
            "why_join": "New reason for joining.",
        }
        resp = student_client.post(reverse("accounts:submit-gi"), new_data)
        assert resp.status_code == status.HTTP_200_OK
        gi = resp.data["general_interest"]
        assert gi["graduation_year"] == 2029
        assert gi["college"] == "New College"
        assert gi["major"] == "New Major"
        assert gi["skills"] == "New Skills"
        assert gi["interest_areas"] == "New Areas"
        assert gi["why_join"] == "New reason for joining."


# GI Validation Tests

@pytest.mark.django_db
class TestGIValidation:

    def test_past_graduation_year_rejected(self, student_client, active_cycle, valid_gi_data):
        """Graduation year in the past is rejected."""
        valid_gi_data["graduation_year"] = 2020
        resp = student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_field(self, student_client, active_cycle):
        """Missing required fields are rejected."""
        resp = student_client.post(
            reverse("accounts:submit-gi"),
            {"graduation_year": 2027},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_empty_why_join_rejected(self, student_client, active_cycle, valid_gi_data):
        """Empty why_join is rejected."""
        valid_gi_data["why_join"] = ""
        resp = student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# View GI Tests

@pytest.mark.django_db
class TestViewGI:

    def test_view_own_gi(self, student_client, student_user, active_cycle, valid_gi_data):
        """Student can view their own GI submission."""
        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)

        resp = student_client.get(reverse("accounts:view-gi"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["graduation_year"] == 2027

    def test_view_gi_not_submitted(self, student_client, active_cycle):
        """Returns 404 when GI hasn't been submitted."""
        resp = student_client.get(reverse("accounts:view-gi"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_view_gi_no_active_cycle(self, student_client):
        """Returns 404 when no active cycle exists."""
        resp = student_client.get(reverse("accounts:view-gi"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# GI Audit Integration Tests

@pytest.mark.django_db
class TestGIAuditLogging:

    def test_gi_submission_creates_audit_log(self, student_client, active_cycle, valid_gi_data):
        """GI submission creates an audit log entry."""
        from apps.audit.models import AuditLog

        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)

        logs = AuditLog.objects.filter(action="GI_SUBMITTED")
        assert logs.count() == 1
        assert "email" in logs.first().metadata
        assert "cycle" in logs.first().metadata

    def test_gi_update_creates_update_audit_log(
        self, student_client, active_cycle, valid_gi_data, updated_gi_data
    ):
        """GI update creates a GI_UPDATED audit log entry."""
        from apps.audit.models import AuditLog

        student_client.post(reverse("accounts:submit-gi"), valid_gi_data)
        student_client.post(reverse("accounts:submit-gi"), updated_gi_data)

        submit_logs = AuditLog.objects.filter(action="GI_SUBMITTED")
        update_logs = AuditLog.objects.filter(action="GI_UPDATED")
        assert submit_logs.count() == 1
        assert update_logs.count() == 1