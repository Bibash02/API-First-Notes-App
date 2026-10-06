from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

_FALLBACK_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}


def api_exception_handler(exc, context):
    """
    One error shape for every failure, so clients only write one parser:

        {"error": {"code": "...", "message": "...", "details": {...}|null}}

    `details` carries per-field messages for validation errors, otherwise null.
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        error = {
            "code": "validation_error",
            "message": "One or more fields are invalid.",
            "details": response.data,
        }
    else:
        codes = exc.get_codes() if hasattr(exc, "get_codes") else None
        code = codes if isinstance(codes, str) else _FALLBACK_CODES.get(response.status_code, "error")
        data = response.data
        message = data.get("detail", "Request failed.") if isinstance(data, dict) else str(data)
        error = {"code": code, "message": str(message), "details": None}

    response.data = {"error": error}
    return response
