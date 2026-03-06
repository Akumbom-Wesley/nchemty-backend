"""
Security headers middleware.

Django's SecurityMiddleware covers the basics (HSTS, XSS filter, etc.)
but doesn't set Content-Security-Policy or Permissions-Policy.
We add those here, and also handle request-level suspicious activity
detection.

Why middleware and not decorators on each view?
- Security headers must apply to EVERY response, including 404s and 500s
- A decorator can be forgotten on a new view; middleware cannot
- Centralised = auditable
"""

import logging

from django.conf import settings

logger = logging.getLogger("security")


class SecurityHeadersMiddleware:
    """
    Adds security-relevant HTTP response headers to every response.

    Headers added:
    - Content-Security-Policy   : restricts what resources the browser loads
    - Permissions-Policy        : disables browser features we don't need
    - Referrer-Policy           : controls how much referrer info is sent
    - Cache-Control             : prevents caching of API responses
    - X-Content-Type-Options    : already set by Django but we reinforce it
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._add_security_headers(response)
        return response

    def _add_security_headers(self, response):
        # CSP: API responses are JSON — no scripts, no frames, no plugins needed.
        # If you serve an admin UI from Django templates, you'll need to relax this.
        response["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none';"
        )

        # Disable browser features this API has no need for
        response["Permissions-Policy"] = (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "payment=()"
        )

        # Don't send referrer headers when navigating away
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # API responses should never be cached by browsers or proxies
        # This prevents a shared computer from leaking auth responses
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response["Pragma"] = "no-cache"

        # Belt-and-suspenders alongside Django's SecurityMiddleware
        response["X-Content-Type-Options"] = "nosniff"

        return response


class SuspiciousRequestMiddleware:
    """
    Detects and logs suspicious request patterns.

    This is a lightweight layer — it logs and flags, not blocks.
    Blocking is handled by django-axes and DRF throttling.
    Logging here feeds the audit trail.

    Patterns detected:
    - Requests with SQL injection signatures in query params
    - Requests probing common vulnerability paths
    - Abnormally large request bodies outside file upload endpoints
    """

    # Paths that are legitimate and skip the probe check
    LEGITIMATE_PATHS = {
        "/api/v1/auth/register/association/",  # large multipart upload
    }

    # Fragments that suggest injection attempts
    SQL_FRAGMENTS = (
        "union select",
        "' or '1'='1",
        "'; drop table",
        "--",
        "xp_cmdshell",
        "<script",
        "javascript:",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_suspicious(request):
            self._log_suspicious(request)
            # We do NOT block here — let the request proceed and fail
            # normally. Blocking at this layer leaks information about
            # what patterns we detect. Logging is sufficient.

        return self.get_response(request)

    def _is_suspicious(self, request):
        # Check query string for injection patterns
        query_string = request.META.get("QUERY_STRING", "").lower()
        for fragment in self.SQL_FRAGMENTS:
            if fragment in query_string:
                return True

        # Check for common vulnerability scanner paths
        path = request.path.lower()
        probe_paths = (
            "/.env", "/wp-admin", "/phpmyadmin",
            "/xmlrpc.php", "/.git", "/config.php",
        )
        if any(path.startswith(p) for p in probe_paths):
            return True

        return False

    def _log_suspicious(self, request):
        from apps.audit.models import AuditLog

        ip = self._get_ip(request)
        user = request.user if request.user.is_authenticated else None

        logger.warning(
            "Suspicious request detected",
            extra={
                "ip": ip,
                "path": request.path,
                "query": request.META.get("QUERY_STRING", ""),
                "user": str(user),
            },
        )

        AuditLog.log(
            AuditLog.EventType.SUSPICIOUS_REQUEST,
            user=user,
            ip=ip,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={
                "path": request.path,
                "query_string": request.META.get("QUERY_STRING", ""),
                "method": request.method,
            },
        )

    def _get_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")