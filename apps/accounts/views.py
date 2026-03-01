"""
Account views.


Rules:
    1. Parse & validate input (via serializer)
    2. Call service method
    3. Return response

NO business logic in views.
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin, IsAdminOrOpsChair
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    ChangeRoleSerializer,
    LaunchTeamCreateSerializer,
    RegisterSerializer,
    UserListSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)
from apps.accounts.services import AccountService


# Public Auth Endpoints
class RegisterView(APIView):
    """
    POST /api/v1/auth/register/

    Self-registration for Northeastern students.
    Requires @northeastern.edu or @husky.neu.edu email.

    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register a new NEU student account",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=UserProfileSerializer,
                description="User successfully registered",
            ),
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="Email already exists"),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AccountService.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
        )

        return Response(
            {
                "message": "Registration successful.",
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/

    Returns JWT access + refresh tokens, plus user profile.

    """

    @extend_schema(
        tags=["Auth"],
        summary="Login and get JWT tokens",
        responses={
            200: OpenApiResponse(description="Tokens + user profile"),
            401: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/v1/auth/token/refresh/

    Refresh an expired access token using a valid refresh token.
    """

    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        responses={
            200: OpenApiResponse(description="New access token"),
            401: OpenApiResponse(description="Invalid/expired refresh token"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# Profile Endpoints (Authenticated)
class MeView(APIView):
    """
    GET  /api/v1/auth/me/  — View own profile
    PATCH /api/v1/auth/me/ — Update own profile (name only)

    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get current user profile",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    @extend_schema(
        tags=["Auth"],
        summary="Update own profile",
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = AccountService.update_profile(
            user=request.user, **serializer.validated_data
        )

        return Response(UserProfileSerializer(user).data)


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/

    Change own password. Requires current password for verification.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Change own password",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Current password incorrect or validation error"),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AccountService.change_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
        )

        return Response({"message": "Password changed successfully."})


# Admin Endpoints
class AdminCreateLaunchTeamView(APIView):
    """
    POST /api/v1/auth/launch-team/

    Admin creates a Launch Team account. Any email domain allowed.

    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Auth"],
        summary="Create Launch Team account (Admin only)",
        request=LaunchTeamCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=UserProfileSerializer,
                description="Launch Team account created",
            ),
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Admin access required"),
            409: OpenApiResponse(description="Email already exists"),
        },
    )
    def post(self, request):
        serializer = LaunchTeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AccountService.create_launch_team_account(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            created_by=request.user,
        )

        return Response(
            {
                "message": "Launch Team account created.",
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminChangeRoleView(APIView):
    """
    PATCH /api/v1/auth/users/{id}/role/

    Admin changes a user's role.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Admin"],
        summary="Change user role (Admin only)",
        request=ChangeRoleSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Invalid role or business rule violation"),
            403: OpenApiResponse(description="Admin access required"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def patch(self, request, user_id):
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AccountService.change_role(
            user_id=user_id,
            new_role=serializer.validated_data["role"],
            changed_by=request.user,
        )

        return Response(UserProfileSerializer(user).data)


class AdminUserListView(APIView):
    """
    GET /api/v1/auth/users/

    List all users. Admin and Ops Chair access.
    Supports filtering by role, is_gi_complete, search by name/email.
    """

    permission_classes = [IsAuthenticated, IsAdminOrOpsChair]

    @extend_schema(
        tags=["Admin"],
        summary="List all users (Admin/Ops Chair)",
        parameters=[
            OpenApiParameter(name="role", description="Filter by role", required=False, type=str, enum=["ADMIN", "OPS_CHAIR", "USER", "LAUNCH_TEAM"]),
            OpenApiParameter(name="is_gi_complete", description="Filter by GI completion", required=False, type=bool),
            OpenApiParameter(name="search", description="Search by name or email", required=False, type=str),
        ],
        responses={200: UserListSerializer(many=True)},
    )
    def get(self, request):
        qs = User.objects.all()

        # Manual filtering (or use django-filter later)
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        gi_complete = request.query_params.get("is_gi_complete")
        if gi_complete is not None:
            qs = qs.filter(is_gi_complete=gi_complete.lower() == "true")

        search = request.query_params.get("search")
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        serializer = UserListSerializer(qs, many=True)
        return Response(serializer.data)