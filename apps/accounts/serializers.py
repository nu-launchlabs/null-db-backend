"""
Account serializers.

Each serializer handles:
    - Input validation (@Valid equivalent)
    - Output serialization (ResponseEntity body)
    - No business logic lives here
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User
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
    # Optional: admin can set a temp password, team member resets later

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