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
from apps.accounts.permissions import IsAdmin, IsAdminOrOpsChair, IsStudentUser
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    ChangeRoleSerializer,
    GIDetailSerializer,
    LaunchTeamCreateSerializer,
    RegisterSerializer,
    SubmitGISerializer,
    UserListSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)
from apps.accounts.services import AccountService
from apps.audit.services import AuditService


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
            ip_address=AuditService.get_ip_from_request(request),
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
            400: OpenApiResponse(
                description="Current password incorrect or validation error"
            ),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AccountService.change_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
            ip_address=AuditService.get_ip_from_request(request),
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
            ip_address=AuditService.get_ip_from_request(request),
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
            400: OpenApiResponse(
                description="Invalid role or business rule violation"
            ),
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
            ip_address=AuditService.get_ip_from_request(request),
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
            OpenApiParameter(
                name="role",
                description="Filter by role",
                required=False,
                type=str,
                enum=["ADMIN", "OPS_CHAIR", "USER", "LAUNCH_TEAM"],
            ),
            OpenApiParameter(
                name="is_gi_complete",
                description="Filter by GI completion",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="search",
                description="Search by name or email",
                required=False,
                type=str,
            ),
        ],
        responses={200: UserListSerializer(many=True)},
    )
    def get(self, request):
        qs = User.objects.all()

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


# General Interest Endpoints (Phase 2)


@extend_schema(tags=["General Interest"])
class SubmitGIView(APIView):
    """
    POST /api/v1/auth/general-interest/
    Submit or update General Interest form. Student only.

    If the student has already submitted a GI for the current cycle,
    this updates it. Otherwise, it creates a new one.
    """

    permission_classes = [IsAuthenticated, IsStudentUser]

    @extend_schema(
        request=SubmitGISerializer,
        responses={
            201: GIDetailSerializer,
            200: GIDetailSerializer,
        },
        summary="Submit or update General Interest form",
        description=(
            "Submit GI for the current active cycle. If already submitted, "
            "updates the existing form. Can be submitted at any time while "
            "a cycle is active."
        ),
    )
    def post(self, request):
        serializer = SubmitGISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gi, created = AccountService.submit_gi(
            user=request.user,
            graduation_year=serializer.validated_data["graduation_year"],
            college=serializer.validated_data["college"],
            major=serializer.validated_data["major"],
            skills=serializer.validated_data["skills"],
            interest_areas=serializer.validated_data["interest_areas"],
            why_join=serializer.validated_data["why_join"],
            ip_address=AuditService.get_ip_from_request(request),
        )

        if created:
            return Response(
                {
                    "message": "General Interest form submitted successfully.",
                    "general_interest": GIDetailSerializer(gi).data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "message": "General Interest form updated successfully.",
                    "general_interest": GIDetailSerializer(gi).data,
                },
                status=status.HTTP_200_OK,
            )


@extend_schema(tags=["General Interest"])
class ViewGIView(APIView):
    """
    GET /api/v1/auth/general-interest/me/
    View own GI submission for the current cycle.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: GIDetailSerializer},
        summary="View own General Interest submission",
        description=(
            "Returns the user's GI submission for the current active cycle, "
            "or 404 if not submitted."
        ),
    )
    def get(self, request):
        gi = AccountService.get_user_gi(user=request.user)

        if gi is None:
            return Response(
                {
                    "message": "No General Interest submission found for the current cycle."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(GIDetailSerializer(gi).data)