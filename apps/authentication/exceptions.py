from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    error_payload = {}

    if isinstance(exc, ValidationError):
        data = response.data

        # Handle both shapes DRF can produce:
        # Shape A (dict):  {"field": ["error"], "non_field_errors": ["error"]}
        # Shape B (list):  ["error message"]  ← this was crashing us
        if isinstance(data, list):
            error_payload = {
                "code": "validation_error",
                "message": _flatten(data)[0] if data else "Validation error.",
            }
        elif isinstance(data, dict):
            field_errors = {}
            non_field = []

            for key, value in data.items():
                if key == "non_field_errors":
                    non_field.extend(_flatten(value))
                else:
                    field_errors[key] = _flatten(value)

            error_payload = {
                "code": "validation_error",
                "message": non_field[0] if non_field else "Please correct the errors below.",
            }
            if field_errors:
                error_payload["fields"] = field_errors
        else:
            error_payload = {
                "code": "validation_error",
                "message": str(data),
            }

    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        error_payload = {
            "code": "authentication_error",
            "message": _flatten(response.data.get("detail", "Authentication required."))[0],
        }

    else:
        detail = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
        error_payload = {
            "code": _get_error_code(response.status_code),
            "message": detail if isinstance(detail, str) else str(detail),
        }

    response.data = {"error": error_payload}
    return response


def _flatten(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _get_error_code(status_code):
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        429: "rate_limit_exceeded",
        500: "server_error",
    }.get(status_code, "error")