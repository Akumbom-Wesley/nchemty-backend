"""
Role-based permission classes for the authentication system.

Design philosophy:
  Permissions answer one question: "is this user allowed to make this request?"
  They should be small, composable, and named after what they allow — not
  what they deny. Views combine them with a list:
    permission_classes = [IsVerifiedUser, IsStudent]

How DRF evaluates a permission list:
  ALL permissions in the list must return True. It's an AND, not an OR.
  For OR logic, inherit from BasePermission and combine manually
  (see IsStudentOrAssociation below for an example).

JWT-aware note:
  These permissions check request.user, which is populated by
  JWTAuthentication from the access token. The user object is
  fetched from DB once per request by simplejwt's authentication
  backend — so checking user.role here does NOT cause extra queries
  beyond what simplejwt already does.
"""

from rest_framework.permissions import BasePermission


class IsVerifiedUser(BasePermission):
    """
    Grants access only to users who are fully verified and active.

    This is the serializers permission for any endpoint that requires a
    complete, approved account — not just a valid JWT.

    Rejects:
    - Students who registered but haven't verified their email
    - Associations still awaiting admin approval
    - Suspended or rejected accounts
    """

    message = "Your account is not yet active. Please complete verification."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_verified   # model property: is_active + status=ACTIVE
        )


class IsStudent(BasePermission):
    """
    Grants access only to users with the 'student' role.
    Should be combined with IsVerifiedUser for protected endpoints:
        permission_classes = [IsVerifiedUser, IsStudent]
    """

    message = "This endpoint is only accessible to students."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.slug == "student"
        )


class IsAssociation(BasePermission):
    """
    Grants access only to users with the 'association' role.
    """

    message = "This endpoint is only accessible to associations."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role
            and request.user.role.slug == "association"
        )


class IsStudentOrAssociation(BasePermission):
    """
    Grants access to either students or associations.
    Example use case: a shared dashboard endpoint accessible to both roles.

    This demonstrates the OR pattern — combine two role checks manually.
    """

    message = "This endpoint is only accessible to students or associations."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role):
            return False
        return request.user.role.slug in ("student", "association")


class HasRole(BasePermission):
    """
    Dynamic permission — checks if the user has any of the specified role slugs.

    Usage in a view:
        def get_permissions(self):
            perm = HasRole()
            perm.allowed_roles = ["student", "corporate"]
            return [IsVerifiedUser(), perm]

    This is the escape hatch for cases where you need role-based access
    without writing a new permission class every time.
    """

    message = "You do not have the required role to access this endpoint."
    allowed_roles: list[str] = []

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role):
            return False
        return request.user.role.slug in self.allowed_roles


class IsSameUserOrStaff(BasePermission):
    """
    Object-level permission: allows access if the requesting user IS the
    object being accessed, OR if they are a staff member.

    Use on user-detail endpoints where users can access their own
    data and admins can access any user's data.

    Example:
        GET /api/v1/users/<id>/   → user can see their own, staff can see all
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        # obj is a User instance on user-detail endpoints
        return request.user.is_staff or obj == request.user