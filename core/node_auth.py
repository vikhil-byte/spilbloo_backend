from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.permissions import BasePermission


User = get_user_model()


class NodeHeaderTokenAuthentication(authentication.BaseAuthentication):
    """
    StarterNode parity auth:
    - Requires Authorization: Bearer <token>
    - Requires user-id header
    - Valid only if tbl_user.activation_key == token and id == user-id
    """

    def authenticate(self, request) -> Optional[Tuple[User, None]]:
        authorization = request.headers.get("Authorization", "")
        user_id = request.headers.get("user-id")

        # If node-style headers are not present, let the next auth backend (JWT) try.
        if not authorization or not authorization.startswith("Bearer ") or not user_id:
            return None

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            return None

        try:
            user = User.objects.get(id=user_id, activation_key=token)
        except User.DoesNotExist:
            # Activation-key auth didn't match; allow JWT auth fallback.
            return None

        return (user, None)


class IsNodePatientOrTherapist(BasePermission):
    """
    StarterNode parity authorization:
    allow only role_id 4 (patient) or 5 (therapist).
    """

    message = "Unauthorized: Insufficient role permissions"

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and int(getattr(user, "role_id", 0)) in (4, 5)):
            return False
        # Enforce strict header/user match only for legacy activation-key auth parity.
        if isinstance(getattr(request, "successful_authenticator", None), NodeHeaderTokenAuthentication):
            header_user_id = request.headers.get("user-id")
            if header_user_id and str(user.id) != str(header_user_id):
                self.message = "Unauthorized: user-id header mismatch"
                return False
        return True
