"""
Custom permission classes for the administration API.

Why not just use IsAdminUser?
- IsAdminUser only checks is_staff=True — no concept of what kind of admin
- We want composable, named permissions that are self-documenting
- Makes it trivial to add a 'reviewer' role later that can approve
  but not suspend accounts

Permission classes are the right place for access control decisions.
Views should not contain if/else logic about who can do what.
"""

from rest_framework.permissions import BasePermission


class IsStaffUser(BasePermission):
    """
    Grants access to users with is_staff=True and is_active=True.

    This is the serializers gate for the entire admin API.
    Every admin endpoint uses this as the minimum requirement.
    """

    message = "You do not have permission to access the administration API."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
        )


class IsSuperUser(BasePermission):
    """
    Grants access only to superusers.

    Reserved for destructive or irreversible operations — e.g.
    permanently deleting records, bulk operations, system config.
    """

    message = "This action requires superuser privileges."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class IsStaffOrReadOnly(BasePermission):
    """
    Read-only access for authenticated users,
    write access only for staff.

    Useful for endpoints where regular users can view
    their own status but only staff can change it.
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user and request.user.is_authenticated
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


class CanReviewApplications(BasePermission):
    """
    Controls who can approve or reject association applications.

    Currently: staff users only.
    Future extension: check for a specific 'reviewer' role or permission
    without changing any view code — just update has_permission here.
    """

    message = "You do not have permission to review applications."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
        )

    def has_object_permission(self, request, view, obj):
        """
        Object-level check: staff can review any application.
        Hook is here so future logic (e.g. regional admin can only
        review associations in their region) has a clean place to live.
        """
        return self.has_permission(request, view)