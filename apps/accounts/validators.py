"""
Email validators for NEU domain enforcement.

Business rules:
    - USER, ADMIN, OPS_CHAIR: Must use @northeastern.edu or @husky.neu.edu
    - LAUNCH_TEAM: Any email allowed (non-NEU startups)
"""

from django.core.exceptions import ValidationError

from utils.constants import NEU_EMAIL_DOMAINS


def validate_neu_email(email: str) -> None:
    """
    Validates that email belongs to a Northeastern domain.

    Raises:
        ValidationError: If domain is not in NEU_EMAIL_DOMAINS.
    """
    domain = email.split("@")[-1].lower()
    if domain not in NEU_EMAIL_DOMAINS:
        raise ValidationError(
            f"A Northeastern email is required (@{' or @'.join(NEU_EMAIL_DOMAINS)})."
        )


def is_neu_email(email: str) -> bool:
    """
    Returns True if email domain is a Northeastern domain.
    Used for setting the is_neu_email flag on User model.
    """
    domain = email.split("@")[-1].lower()
    return domain in NEU_EMAIL_DOMAINS