"""
Phase 1 tests — Auth endpoints, permissions, and business rules.

Run with: make test
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

# Fixtures (reusable test setup)

@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def neu_user_data():
    """Valid NEU student registration data."""
    return {
        "email": "test.student@northeastern.edu",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "first_name": "Test",
        "last_name": "Student",
    }


@pytest.fixture
def husky_user_data():
    """Valid Husky email registration data."""
    return {
        "email": "student@husky.neu.edu",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "first_name": "Husky",
        "last_name": "Student",
    }


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
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
    """Create an ops chair user."""
    return User.objects.create_user(
        email="ops@northeastern.edu",
        password="OpsPass123!",
        first_name="Ops",
        last_name="Chair",
        role=User.Role.OPS_CHAIR,
    )


@pytest.fixture
def student_user(db):
    """Create a regular student user."""
    return User.objects.create_user(
        email="student@northeastern.edu",
        password="StudentPass123!",
        first_name="Regular",
        last_name="Student",
        role=User.Role.USER,
    )


@pytest.fixture
def launch_team_user(db):
    """Create a launch team user (non-NEU email)."""
    return User.objects.create_user(
        email="startup@techcompany.com",
        password="LaunchPass123!",
        first_name="Startup",
        last_name="Founder",
        role=User.Role.LAUNCH_TEAM,
        is_neu_email=False,
    )


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def student_client(api_client, student_user):
    """API client authenticated as student."""
    api_client.force_authenticate(user=student_user)
    return api_client


# Registration Tests

@pytest.mark.django_db
class TestRegistration:

    def test_register_success_neu_email(self, api_client, neu_user_data):
        """NEU student can register successfully."""
        resp = api_client.post(reverse("accounts:register"), neu_user_data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["user"]["email"] == neu_user_data["email"]
        assert resp.data["user"]["role"] == "USER"
        assert resp.data["user"]["is_neu_email"] is True
        assert User.objects.filter(email=neu_user_data["email"]).exists()

    def test_register_success_husky_email(self, api_client, husky_user_data):
        """Husky email is also accepted."""
        resp = api_client.post(reverse("accounts:register"), husky_user_data)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_register_fail_non_neu_email(self, api_client):
        """Non-NEU email is rejected for self-registration."""
        data = {
            "email": "user@gmail.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "first_name": "External",
            "last_name": "User",
        }
        resp = api_client.post(reverse("accounts:register"), data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_fail_duplicate_email(self, api_client, neu_user_data, student_user):
        """Duplicate email is rejected."""
        neu_user_data["email"] = student_user.email
        resp = api_client.post(reverse("accounts:register"), neu_user_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_fail_password_mismatch(self, api_client, neu_user_data):
        """Mismatched passwords are rejected."""
        neu_user_data["confirm_password"] = "DifferentPass!"
        resp = api_client.post(reverse("accounts:register"), neu_user_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_fail_weak_password(self, api_client, neu_user_data):
        """Weak password is rejected."""
        neu_user_data["password"] = "123"
        neu_user_data["confirm_password"] = "123"
        resp = api_client.post(reverse("accounts:register"), neu_user_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Login Tests

@pytest.mark.django_db
class TestLogin:

    def test_login_success(self, api_client, student_user):
        """Valid credentials return JWT tokens + user profile."""
        resp = api_client.post(
            reverse("accounts:login"),
            {"email": student_user.email, "password": "StudentPass123!"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data
        assert resp.data["user"]["role"] == "USER"

    def test_login_fail_wrong_password(self, api_client, student_user):
        """Wrong password returns 401."""
        resp = api_client.post(
            reverse("accounts:login"),
            {"email": student_user.email, "password": "WrongPassword!"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_fail_nonexistent_user(self, api_client):
        """Non-existent email returns 401."""
        resp = api_client.post(
            reverse("accounts:login"),
            {"email": "nobody@northeastern.edu", "password": "Whatever123!"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# Token Refresh Tests

@pytest.mark.django_db
class TestTokenRefresh:

    def test_refresh_success(self, api_client, student_user):
        """Valid refresh token returns new access token."""
        login = api_client.post(
            reverse("accounts:login"),
            {"email": student_user.email, "password": "StudentPass123!"},
        )
        resp = api_client.post(
            reverse("accounts:token-refresh"),
            {"refresh": login.data["refresh"]},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data


# Profile Tests

@pytest.mark.django_db
class TestProfile:

    def test_get_me(self, student_client, student_user):
        """Authenticated user can view own profile."""
        resp = student_client.get(reverse("accounts:me"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["email"] == student_user.email

    def test_get_me_unauthenticated(self, api_client):
        """Unauthenticated request returns 401."""
        resp = api_client.get(reverse("accounts:me"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_me(self, student_client):
        """User can update own name."""
        resp = student_client.patch(
            reverse("accounts:me"),
            {"first_name": "Updated"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["first_name"] == "Updated"

    def test_change_password(self, student_client):
        """User can change own password."""
        resp = student_client.post(
            reverse("accounts:change-password"),
            {
                "current_password": "StudentPass123!",
                "new_password": "NewSecurePass456!",
                "confirm_new_password": "NewSecurePass456!",
            },
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_change_password_wrong_current(self, student_client):
        """Wrong current password is rejected."""
        resp = student_client.post(
            reverse("accounts:change-password"),
            {
                "current_password": "WrongPassword!",
                "new_password": "NewSecurePass456!",
                "confirm_new_password": "NewSecurePass456!",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Launch Team Creation Tests

@pytest.mark.django_db
class TestLaunchTeamCreation:

    def test_admin_creates_launch_team(self, authenticated_client):
        """Admin can create Launch Team account with any email."""
        data = {
            "email": "founder@startup.io",
            "password": "StartupPass123!",
            "first_name": "Jane",
            "last_name": "Founder",
        }
        resp = authenticated_client.post(reverse("accounts:create-launch-team"), data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["user"]["role"] == "LAUNCH_TEAM"
        assert resp.data["user"]["is_neu_email"] is False

    def test_admin_creates_launch_team_neu_email(self, authenticated_client):
        """Launch Team with NEU email is also valid."""
        data = {
            "email": "also.student@northeastern.edu",
            "password": "NeuPass123!",
            "first_name": "NEU",
            "last_name": "Founder",
        }
        resp = authenticated_client.post(reverse("accounts:create-launch-team"), data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["user"]["is_neu_email"] is True

    def test_student_cannot_create_launch_team(self, student_client):
        """Student role cannot create Launch Team accounts."""
        data = {
            "email": "founder@startup.io",
            "password": "StartupPass123!",
            "first_name": "Jane",
            "last_name": "Founder",
        }
        resp = student_client.post(reverse("accounts:create-launch-team"), data)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_create_launch_team(self, api_client):
        """Unauthenticated request gets 401."""
        data = {
            "email": "founder@startup.io",
            "password": "StartupPass123!",
            "first_name": "Jane",
            "last_name": "Founder",
        }
        resp = api_client.post(reverse("accounts:create-launch-team"), data)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# Role Management Tests

@pytest.mark.django_db
class TestRoleManagement:

    def test_admin_changes_role(self, authenticated_client, student_user):
        """Admin can change a user's role."""
        resp = authenticated_client.patch(
            reverse("accounts:change-role", kwargs={"user_id": student_user.id}),
            {"role": "OPS_CHAIR"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["role"] == "OPS_CHAIR"

    def test_admin_cannot_change_own_role(self, authenticated_client, admin_user):
        """Admin cannot change their own role."""
        resp = authenticated_client.patch(
            reverse("accounts:change-role", kwargs={"user_id": admin_user.id}),
            {"role": "USER"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_assign_admin_to_non_neu(self, authenticated_client, launch_team_user):
        """Cannot give ADMIN role to non-NEU email user."""
        resp = authenticated_client.patch(
            reverse("accounts:change-role", kwargs={"user_id": launch_team_user.id}),
            {"role": "ADMIN"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_student_cannot_change_roles(self, student_client, admin_user):
        """Student cannot change anyone's role."""
        resp = student_client.patch(
            reverse("accounts:change-role", kwargs={"user_id": admin_user.id}),
            {"role": "USER"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# User List Tests (Admin)

@pytest.mark.django_db
class TestAdminUserList:

    def test_admin_can_list_users(self, authenticated_client, student_user):
        """Admin can see all users."""
        resp = authenticated_client.get(reverse("accounts:user-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 2  # admin + student

    def test_filter_by_role(self, authenticated_client, student_user):
        """Admin can filter users by role."""
        resp = authenticated_client.get(
            reverse("accounts:user-list"), {"role": "USER"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert all(u["role"] == "USER" for u in resp.data)

    def test_search_users(self, authenticated_client, student_user):
        """Admin can search users by name/email."""
        resp = authenticated_client.get(
            reverse("accounts:user-list"), {"search": "Regular"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_student_cannot_list_users(self, student_client):
        """Student cannot access user list."""
        resp = student_client.get(reverse("accounts:user-list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# Model Tests

@pytest.mark.django_db
class TestUserModel:

    def test_create_user(self, db):
        """User creation works with email as identifier."""
        user = User.objects.create_user(
            email="test@northeastern.edu",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
        )
        assert user.email == "test@northeastern.edu"
        assert user.role == User.Role.USER
        assert user.is_active is True
        assert user.is_staff is False
        assert user.check_password("TestPass123!")

    def test_create_superuser(self, db):
        """Superuser gets ADMIN role and staff permissions."""
        user = User.objects.create_superuser(
            email="super@northeastern.edu",
            password="SuperPass123!",
            first_name="Super",
            last_name="Admin",
        )
        assert user.role == User.Role.ADMIN
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_user_str(self, student_user):
        """String representation includes name and email."""
        assert student_user.email in str(student_user)

    def test_computed_properties(self, admin_user, student_user, launch_team_user):
        """Role-check properties work correctly."""
        assert admin_user.is_admin is True
        assert admin_user.is_student is False
        assert student_user.is_student is True
        assert launch_team_user.is_launch_team is True