"""
Authentication and authorization middleware.
"""

from typing import Optional

from bot.config import get_config
from bot.exceptions import AuthenticationError, AuthorizationError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class AuthMiddleware:
    """Authentication and authorization checks."""

    def __init__(self):
        """Initialize auth middleware."""
        self.config = get_config()

    def check_user_allowed(self, user_id: int, username: Optional[str] = None) -> bool:
        """Check if user is allowed to use bot."""
        is_allowed = (
            user_id in self.config.admin_ids or
            user_id in self.config.allowed_user_ids
        )

        if not is_allowed:
            logger.warning(
                "Unauthorized access attempt",
                extra={'user_id': user_id, 'username': username}
            )

        return is_allowed

    def check_admin(self, user_id: int, username: Optional[str] = None) -> bool:
        """Check if user is admin."""
        is_admin = user_id in self.config.admin_ids

        if not is_admin:
            logger.warning(
                "Admin access denied",
                extra={'user_id': user_id, 'username': username}
            )

        return is_admin

    def check_permission(
        self,
        user_id: int,
        permission: str,
        username: Optional[str] = None,
    ) -> bool:
        """Check if user has specific permission."""
        # Admins have all permissions
        if self.check_admin(user_id):
            return True

        # For now, all allowed users have same permissions
        return self.check_user_allowed(user_id)

    def require_user_allowed(self, user_id: int, username: Optional[str] = None) -> None:
        """Require user to be allowed, raise if not."""
        if not self.check_user_allowed(user_id, username):
            raise AuthenticationError(
                f"User {user_id} is not allowed to use this bot"
            )

    def require_admin(self, user_id: int, username: Optional[str] = None) -> None:
        """Require user to be admin, raise if not."""
        if not self.check_admin(user_id, username):
            raise AuthorizationError(
                f"User {user_id} is not an admin"
            )

    def require_permission(
        self,
        user_id: int,
        permission: str,
        username: Optional[str] = None,
    ) -> None:
        """Require user to have permission, raise if not."""
        if not self.check_permission(user_id, permission, username):
            raise AuthorizationError(
                f"User {user_id} does not have permission: {permission}"
            )

    def get_user_role(self, user_id: int) -> str:
        """Get user role."""
        if self.check_admin(user_id):
            return "admin"
        elif self.check_user_allowed(user_id):
            return "user"
        else:
            return "unauthorized"

    def log_access(
        self,
        user_id: int,
        action: str,
        username: Optional[str] = None,
        allowed: bool = True,
    ) -> None:
        """Log user access."""
        status = "allowed" if allowed else "denied"
        logger.info(
            f"User action: {action} ({status})",
            extra={
                'user_id': user_id,
                'username': username,
                'action': action,
            }
        )


# Global auth middleware instance
_auth = None


def get_auth() -> AuthMiddleware:
    """Get or create the global auth middleware."""
    global _auth
    if _auth is None:
        _auth = AuthMiddleware()
    return _auth


def reset_auth() -> None:
    """Reset the global auth middleware (useful for testing)."""
    global _auth
    _auth = None
