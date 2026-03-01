"""
Custom exception classes and handler for consistent API error responses.

"""

import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# Custom Exception Classes
class BusinessLogicError(APIException):
    """
    Raised when a business rule is violated.
    e.g., "Complete General Interest form first"

    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A business rule was violated."
    default_code = "business_logic_error"


class ConflictError(APIException):
    """
    Raised when an operation conflicts with existing state.
    e.g., "User is already assigned to a project this cycle"

    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This operation conflicts with existing data."
    default_code = "conflict"


class ResourceNotFoundError(APIException):
    """
    Raised when a requested resource doesn't exist.

    """

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class ForbiddenError(APIException):
    """
    Raised when user has auth but lacks permission for this specific resource.

    """

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "forbidden"


# Custom Exception Handler
def custom_exception_handler(exc, context):
    """
    Wraps DRF's default handler to produce consistent error responses.

    Response format:
    {
        "error": {
            "code": "business_logic_error",
            "message": "Complete General Interest form first",
            "details": null
        }
    }
    """
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — log it, return 500
        logger.exception("Unhandled exception: %s", exc)
        return None

    # Build consistent error body
    error_code = getattr(exc, "default_code", "error")
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, str):
            error_code = codes

    # Handle DRF's various error formats
    if isinstance(response.data, dict):
        # Field-level validation errors → put in details
        if "detail" in response.data:
            message = str(response.data["detail"])
            details = None
        else:
            message = "Validation error"
            details = response.data
    elif isinstance(response.data, list):
        message = response.data[0] if response.data else "An error occurred"
        details = None
    else:
        message = str(response.data)
        details = None

    response.data = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
        }
    }

    return response