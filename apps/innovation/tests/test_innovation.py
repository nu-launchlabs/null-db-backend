"""
Comprehensive tests for the Innovation Track (Phase 4).

Covers:
    - Proposal submission, approval, rejection
    - Preference submission, update, validation
    - Innovation assignment + conflict detection
    - Permission checks for all roles
    - Edge cases: duplicate proposals, proposal-blocks-preferences, etc.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.cycles.models import ApplicationCycle, Assignment
from apps.innovation.choices import ProposalStatus
from apps.innovation.models import InnovationPreference, InnovationProject, Proposals


# ══════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def cycle(db):
    return ApplicationCycle.objects.create(
        name="Fall 2026",
        is_active=True,
        launch_open=False,
        innovation_open=True,
    )


@pytest.fixture
def closed_innovation_cycle(db):
    return ApplicationCycle.objects.create(
        name="Spring 2026",
        is_active=True,
        launch_open=False,
        innovation_open=False,
    )


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(
        email="admin@test.com",
        password="testpass123",
        first_name="Admin",
        last_name="User",
        role=User.Role.ADMIN,
    )
    u.is_gi_complete = True
    u.save()
    return u


@pytest.fixture
def ops_user(db):
    u = User.objects.create_user(
        email="ops@test.com",
        password="testpass123",
        first_name="Ops",
        last_name="Chair",
        role=User.Role.OPS_CHAIR,
    )
    u.is_gi_complete = True
    u.save()
    return u


@pytest.fixture
def student(db):
    u = User.objects.create_user(
        email="student@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Student",
        role=User.Role.USER,
    )
    u.is_gi_complete = True
    u.save()
    return u


@pytest.fixture
def student2(db):
    u = User.objects.create_user(
        email="student2@test.com",
        password="testpass123",
        first_name="Second",
        last_name="Student",
        role=User.Role.USER,
    )
    u.is_gi_complete = True
    u.save()
    return u


@pytest.fixture
def student_no_gi(db):
    return User.objects.create_user(
        email="nogi@test.com",
        password="testpass123",
        first_name="No",
        last_name="GI",
        role=User.Role.USER,
    )


@pytest.fixture
def launch_team_user(db):
    return User.objects.create_user(
        email="team@test.com",
        password="testpass123",
        first_name="Launch",
        last_name="Team",
        role=User.Role.LAUNCH_TEAM,
    )


def auth(api, user):
    token = RefreshToken.for_user(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")


# ══════════════════════════════════════════════
# Proposal Tests
# ══════════════════════════════════════════════


@pytest.mark.django_db
class TestSubmitProposal:

    def test_submit_proposal_success(self, api, student, cycle):
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-proposal"),
            {
                "title": "AI Tutor",
                "description": "An AI-powered tutoring platform.",
                "tech_stack": "Python, React",
                "max_members": 5,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.data["proposal"]["title"] == "AI Tutor"
        assert r.data["proposal"]["status"] == "SUBMITTED"
        assert Proposals.objects.filter(proposer=student).count() == 1

    def test_submit_proposal_duplicate(self, api, student, cycle):
        auth(api, student)
        data = {"title": "Project A", "description": "Desc"}
        api.post(reverse("innovation:submit-proposal"), data, format="json")
        r = api.post(reverse("innovation:submit-proposal"), data, format="json")
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_submit_proposal_innovation_closed(self, api, student, closed_innovation_cycle):
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-proposal"),
            {"title": "X", "description": "Y"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_proposal_no_gi(self, api, student_no_gi, cycle):
        auth(api, student_no_gi)
        r = api.post(
            reverse("innovation:submit-proposal"),
            {"title": "X", "description": "Y"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_submit_proposal_admin_forbidden(self, api, admin_user, cycle):
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:submit-proposal"),
            {"title": "X", "description": "Y"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_submit_proposal_already_assigned(self, api, student, cycle, launch_team_user):
        from apps.launch.models import LaunchProject

        proj = LaunchProject.objects.create(
            cycle=cycle,
            team=launch_team_user,
            title="Startup",
            description="D",
        )
        Assignment.objects.create(
            user=student,
            cycle=cycle,
            track=Assignment.Track.LAUNCH,
            launch_project=proj,
            assigned_by=launch_team_user,
        )
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-proposal"),
            {"title": "X", "description": "Y"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMyProposal:

    def test_my_proposal_exists(self, api, student, cycle):
        Proposals.objects.create(
            cycle=cycle,
            proposer=student,
            title="My Proj",
            description="Desc",
        )
        auth(api, student)
        r = api.get(reverse("innovation:my-proposal"))
        assert r.status_code == status.HTTP_200_OK
        assert r.data["title"] == "My Proj"

    def test_my_proposal_not_found(self, api, student, cycle):
        auth(api, student)
        r = api.get(reverse("innovation:my-proposal"))
        assert r.status_code == status.HTTP_404_NOT_FOUND


# ══════════════════════════════════════════════
# Proposal Review Tests (Admin/Ops)
# ══════════════════════════════════════════════


@pytest.mark.django_db
class TestProposalReview:

    def test_list_proposals_admin(self, api, admin_user, student, cycle):
        Proposals.objects.create(
            cycle=cycle, proposer=student, title="P1", description="D1"
        )
        auth(api, admin_user)
        r = api.get(reverse("innovation:proposal-list"))
        assert r.status_code == status.HTTP_200_OK
        assert len(r.data) == 1

    def test_list_proposals_filter_by_status(self, api, admin_user, student, cycle):
        Proposals.objects.create(
            cycle=cycle, proposer=student, title="P1", description="D",
            status=ProposalStatus.SUBMITTED,
        )
        auth(api, admin_user)
        r = api.get(reverse("innovation:proposal-list") + "?status=APPROVED")
        assert r.status_code == status.HTTP_200_OK
        assert len(r.data) == 0

    def test_list_proposals_student_forbidden(self, api, student, cycle):
        auth(api, student)
        r = api.get(reverse("innovation:proposal-list"))
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_proposal(self, api, admin_user, student, cycle):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="AI Bot", description="D"
        )
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:approve-proposal", kwargs={"proposal_id": p.id})
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.data["proposal"]["status"] == "APPROVED"
        assert r.data["project"]["title"] == "AI Bot"
        assert r.data["project"]["lead_email"] == student.email
        assert InnovationProject.objects.filter(proposal=p).exists()

    def test_approve_already_approved(self, api, admin_user, student, cycle):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="X", description="D",
            status=ProposalStatus.APPROVED,
        )
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:approve-proposal", kwargs={"proposal_id": p.id})
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_reject_proposal(self, api, ops_user, student, cycle):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="Rej", description="D"
        )
        auth(api, ops_user)
        r = api.post(
            reverse("innovation:reject-proposal", kwargs={"proposal_id": p.id})
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.data["proposal"]["status"] == "REJECTED"

    def test_reject_already_rejected(self, api, admin_user, student, cycle):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="X", description="D",
            status=ProposalStatus.REJECTED,
        )
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:reject-proposal", kwargs={"proposal_id": p.id})
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


# ══════════════════════════════════════════════
# Innovation Project Tests
# ══════════════════════════════════════════════


@pytest.mark.django_db
class TestInnovationProjects:

    def _make_project(self, cycle, student):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="Proj",
            description="D", status=ProposalStatus.APPROVED,
        )
        return InnovationProject.objects.create(
            proposal=p, cycle=cycle, lead=student, title="Proj",
        )

    def test_list_projects(self, api, student, cycle):
        self._make_project(cycle, student)
        auth(api, student)
        r = api.get(reverse("innovation:project-list"))
        assert r.status_code == status.HTTP_200_OK
        assert len(r.data) == 1

    def test_project_detail(self, api, student, cycle):
        proj = self._make_project(cycle, student)
        auth(api, student)
        r = api.get(
            reverse("innovation:project-detail", kwargs={"project_id": proj.id})
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.data["title"] == "Proj"

    def test_project_not_found(self, api, student, cycle):
        auth(api, student)
        r = api.get(
            reverse("innovation:project-detail", kwargs={"project_id": 9999})
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND


# ══════════════════════════════════════════════
# Preference Tests
# ══════════════════════════════════════════════


@pytest.mark.django_db
class TestPreferences:

    def _make_projects(self, cycle, admin_user):
        """Create 3 approved Innovation projects for testing."""
        projects = []
        for i in range(1, 4):
            u = User.objects.create_user(
                email=f"lead{i}@test.com",
                password="testpass123",
                first_name=f"Lead{i}",
                last_name="User",
                role=User.Role.USER,
            )
            p = Proposals.objects.create(
                cycle=cycle, proposer=u, title=f"Project {i}",
                description=f"Desc {i}", status=ProposalStatus.APPROVED,
            )
            proj = InnovationProject.objects.create(
                proposal=p, cycle=cycle, lead=u, title=f"Project {i}",
            )
            projects.append(proj)
        return projects

    def test_submit_preferences_success(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {
                "preferences": [
                    {"project_id": projs[0].id, "rank": 1},
                    {"project_id": projs[1].id, "rank": 2},
                    {"project_id": projs[2].id, "rank": 3},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert len(r.data["preferences"]) == 3
        assert InnovationPreference.objects.filter(user=student).count() == 3

    def test_submit_preferences_replaces_existing(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        # First submission
        api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[0].id, "rank": 1}]},
            format="json",
        )
        # Second submission replaces
        r = api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[1].id, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        prefs = InnovationPreference.objects.filter(user=student)
        assert prefs.count() == 1
        assert prefs.first().project_id == projs[1].id

    def test_update_preferences_via_put(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.put(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[2].id, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK

    def test_preferences_duplicate_rank(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {
                "preferences": [
                    {"project_id": projs[0].id, "rank": 1},
                    {"project_id": projs[1].id, "rank": 1},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_preferences_duplicate_project(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {
                "preferences": [
                    {"project_id": projs[0].id, "rank": 1},
                    {"project_id": projs[0].id, "rank": 2},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_preferences_more_than_3(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        # Create a 4th project
        u4 = User.objects.create_user(
            email="lead4@test.com", password="testpass123",
            first_name="L4", last_name="U", role=User.Role.USER,
        )
        p4 = Proposals.objects.create(
            cycle=cycle, proposer=u4, title="P4",
            description="D", status=ProposalStatus.APPROVED,
        )
        proj4 = InnovationProject.objects.create(
            proposal=p4, cycle=cycle, lead=u4, title="P4",
        )
        r = api.post(
            reverse("innovation:submit-preferences"),
            {
                "preferences": [
                    {"project_id": projs[0].id, "rank": 1},
                    {"project_id": projs[1].id, "rank": 2},
                    {"project_id": projs[2].id, "rank": 3},
                    {"project_id": proj4.id, "rank": 1},
                ]
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_preferences_blocked_by_pending_proposal(self, api, student, cycle, admin_user):
        Proposals.objects.create(
            cycle=cycle, proposer=student, title="My Prop",
            description="D", status=ProposalStatus.SUBMITTED,
        )
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[0].id, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_preferences_blocked_by_approved_proposal(self, api, student, cycle, admin_user):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="Approved",
            description="D", status=ProposalStatus.APPROVED,
        )
        InnovationProject.objects.create(
            proposal=p, cycle=cycle, lead=student, title="Approved",
        )
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[0].id, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_preferences_allowed_after_rejection(self, api, student, cycle, admin_user):
        Proposals.objects.create(
            cycle=cycle, proposer=student, title="Rejected",
            description="D", status=ProposalStatus.REJECTED,
        )
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[0].id, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_preferences_blocked_by_assignment(self, api, student, cycle, admin_user, launch_team_user):
        from apps.launch.models import LaunchProject

        lp = LaunchProject.objects.create(
            cycle=cycle, team=launch_team_user, title="S", description="D",
        )
        Assignment.objects.create(
            user=student, cycle=cycle, track=Assignment.Track.LAUNCH,
            launch_project=lp, assigned_by=launch_team_user,
        )
        projs = self._make_projects(cycle, admin_user)
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": projs[0].id, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_preferences_innovation_closed(self, api, student, closed_innovation_cycle, admin_user):
        auth(api, student)
        r = api.post(
            reverse("innovation:submit-preferences"),
            {"preferences": [{"project_id": 1, "rank": 1}]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_my_preferences(self, api, student, cycle, admin_user):
        projs = self._make_projects(cycle, admin_user)
        InnovationPreference.objects.create(
            user=student, project=projs[0], cycle=cycle, rank=1,
        )
        auth(api, student)
        r = api.get(reverse("innovation:my-preferences"))
        assert r.status_code == status.HTTP_200_OK
        assert len(r.data) == 1

    def test_project_preferences_admin(self, api, admin_user, student, student2, cycle):
        p = Proposals.objects.create(
            cycle=cycle, proposer=admin_user, title="AP",
            description="D", status=ProposalStatus.APPROVED,
        )
        proj = InnovationProject.objects.create(
            proposal=p, cycle=cycle, lead=admin_user, title="AP",
        )
        InnovationPreference.objects.create(
            user=student, project=proj, cycle=cycle, rank=1,
        )
        InnovationPreference.objects.create(
            user=student2, project=proj, cycle=cycle, rank=2,
        )
        auth(api, admin_user)
        r = api.get(
            reverse(
                "innovation:project-preferences",
                kwargs={"project_id": proj.id},
            )
        )
        assert r.status_code == status.HTTP_200_OK
        assert len(r.data) == 2

    def test_project_preferences_student_forbidden(self, api, student, cycle):
        auth(api, student)
        r = api.get(
            reverse(
                "innovation:project-preferences",
                kwargs={"project_id": 1},
            )
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN


# ══════════════════════════════════════════════
# Assignment Tests
# ══════════════════════════════════════════════


@pytest.mark.django_db
class TestInnovationAssignment:

    def _make_project(self, cycle, student):
        p = Proposals.objects.create(
            cycle=cycle, proposer=student, title="Proj",
            description="D", status=ProposalStatus.APPROVED,
        )
        return InnovationProject.objects.create(
            proposal=p, cycle=cycle, lead=student, title="Proj",
        )

    def test_assign_success(self, api, admin_user, student2, cycle, student):
        proj = self._make_project(cycle, student)
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": student2.id, "project_id": proj.id},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.data["track"] == "INNOVATION"
        assert Assignment.objects.filter(
            user=student2, cycle=cycle
        ).exists()

    def test_assign_duplicate(self, api, admin_user, student2, cycle, student):
        proj = self._make_project(cycle, student)
        auth(api, admin_user)
        api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": student2.id, "project_id": proj.id},
            format="json",
        )
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": student2.id, "project_id": proj.id},
            format="json",
        )
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_assign_already_on_launch(self, api, admin_user, student2, cycle, student, launch_team_user):
        from apps.launch.models import LaunchProject

        lp = LaunchProject.objects.create(
            cycle=cycle, team=launch_team_user, title="S", description="D",
        )
        Assignment.objects.create(
            user=student2, cycle=cycle, track=Assignment.Track.LAUNCH,
            launch_project=lp, assigned_by=launch_team_user,
        )
        proj = self._make_project(cycle, student)
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": student2.id, "project_id": proj.id},
            format="json",
        )
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_assign_team_full(self, api, admin_user, cycle, student):
        proj = self._make_project(cycle, student)
        proj.max_members = 1
        proj.save()
        # Fill the team
        Assignment.objects.create(
            user=student, cycle=cycle, track=Assignment.Track.INNOVATION,
            innovation_project=proj, assigned_by=admin_user,
        )
        # Try to add another
        s3 = User.objects.create_user(
            email="s3@test.com", password="testpass123",
            first_name="S3", last_name="U", role=User.Role.USER,
        )
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": s3.id, "project_id": proj.id},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_non_student(self, api, admin_user, cycle, student, launch_team_user):
        proj = self._make_project(cycle, student)
        auth(api, admin_user)
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": launch_team_user.id, "project_id": proj.id},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_student_forbidden(self, api, student, student2, cycle):
        auth(api, student)
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": student2.id, "project_id": 1},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_ops_chair_allowed(self, api, ops_user, student2, cycle, student):
        proj = self._make_project(cycle, student)
        auth(api, ops_user)
        r = api.post(
            reverse("innovation:assign-to-innovation"),
            {"user_id": student2.id, "project_id": proj.id},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED