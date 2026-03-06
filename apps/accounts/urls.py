from django.urls import path
from apps.accounts.views import SubmitGIView, ViewGIView

from apps.accounts.views import (
    AdminChangeRoleView,
    AdminCreateLaunchTeamView,
    AdminUserListView,
    ChangePasswordView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    MeView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    # Public
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    # Authenticated
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    # Admin
    path("launch-team/", AdminCreateLaunchTeamView.as_view(), name="create-launch-team"),
    path("users/", AdminUserListView.as_view(), name="user-list"),
    path("users/<int:user_id>/role/", AdminChangeRoleView.as_view(), name="change-role"),
    
    # General Interest (Phase 2)
    # POST /api/v1/auth/general-interest/  Submit GI (Student)
    # GET  /api/v1/auth/general-interest/  View own GI (Authenticated)
    path("general-interest/", SubmitGIView.as_view(), name="submit-gi"),
    path("general-interest/me/", ViewGIView.as_view(), name="view-gi"),
]