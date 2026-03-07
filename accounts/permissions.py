from rest_framework import permissions
from .models import User

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to users with the Admin role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role_id == User.ROLE_ADMIN
        )

class IsManagerUser(permissions.BasePermission):
    """
    Allows access only to users with the Manager role or higher.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role_id in [User.ROLE_ADMIN, User.ROLE_MANAGER]
        )
