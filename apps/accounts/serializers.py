"""
Account serializers.

Each serializer handles:
    - Input validation (@Valid equivalent)
    - Output serialization (ResponseEntity body)
    - No business logic lives here
"""

import datetime

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import GeneralInterest, User
from apps.accounts.validators import validate_neu_email


# Auth Serializers


class RegisterSerializer(serializers.Serializer):
    """
    Only NEU emails allowed for self-registration.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value):
        email = value.lower().strip()
        validate_neu_email(email)
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return data


class LaunchTeamCreateSerializer(serializers.Serializer):
    """
    Any email domain is allowed.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends JWT token to include role and user info in the response.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to the JWT payload
        token["role"] = user.role
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Also include user info in the response body (not just token)
        data["user"] = UserProfileSerializer(self.user).data
        return data


# Profile Serializers


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only representation of the user.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_gi_complete",
            "is_neu_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Only first_name and last_name are editable by the user.
    Role, email, is_gi_complete are controlled by the system.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class ChangePasswordSerializer(serializers.Serializer):
    """Password change."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."}
            )
        return data


# Admin Serializers


class ChangeRoleSerializer(serializers.Serializer):
    """Input for admin changing a user's role."""

    role = serializers.ChoiceField(choices=User.Role.choices)


class UserListSerializer(serializers.ModelSerializer):
    """
    Output for admin user listing.
    Lightweight - no sensitive fields.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_gi_complete",
            "is_neu_email",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


# General Interest Serializers (Phase 2)


class SubmitGISerializer(serializers.Serializer):
    """Input DTO for submitting General Interest form."""

    graduation_year = serializers.IntegerField(
        min_value=2024,
        max_value=2035,
        help_text="Expected graduation year",
    )
    college = serializers.CharField(
        max_length=200,
        help_text='College within NEU, e.g. "Khoury College of Computer Sciences"',
    )
    major = serializers.CharField(
        max_length=200,
        help_text='Major/program, e.g. "Computer Science"',
    )
    skills = serializers.CharField(
        help_text="Technical and non-technical skills",
    )
    interest_areas = serializers.CharField(
        help_text="Areas of interest: product, engineering, design, marketing, etc.",
    )
    why_join = serializers.CharField(
        help_text="Why do you want to join NU Launch Labs?",
    )

    def validate_graduation_year(self, value):
        """Ensure graduation year is reasonable."""
        current_year = datetime.date.today().year
        if value < current_year:
            raise serializers.ValidationError(
                "Graduation year cannot be in the past."
            )
        return value


class GIDetailSerializer(serializers.ModelSerializer):
    """Output DTO for GI submission details."""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    cycle_name = serializers.CharField(source="cycle.name", read_only=True)

    class Meta:
        model = GeneralInterest
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "cycle",
            "cycle_name",
            "graduation_year",
            "college",
            "major",
            "skills",
            "interest_areas",
            "why_join",
            "submitted_at",
        ]
        read_only_fields = fields