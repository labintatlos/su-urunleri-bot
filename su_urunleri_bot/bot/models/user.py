"""
User model with permissions and profile information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set

from bot.config import get_config


@dataclass
class User:
    """User model."""

    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    last_seen: Optional[datetime] = None
    custom_name: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.custom_name:
            return self.custom_name
        parts = [self.first_name or '', self.last_name or '']
        return ' '.join(p for p in parts if p).strip() or f"User {self.user_id}"

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        if self.custom_name:
            return self.custom_name
        if self.first_name:
            return self.first_name
        if self.username:
            return f"@{self.username}"
        return f"ID: {self.user_id}"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        config = get_config()
        return self.user_id in config.admin_ids

    @property
    def is_allowed(self) -> bool:
        """Check if user is allowed to use bot."""
        config = get_config()
        return (
            self.user_id in config.admin_ids or
            self.user_id in config.allowed_user_ids
        )

    @property
    def is_authorized(self) -> bool:
        """Check if user is authorized (alias for is_allowed)."""
        return self.is_allowed

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        if self.is_admin:
            return True
        return permission in self.permissions

    def grant_permission(self, permission: str) -> None:
        """Grant permission to user."""
        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        """Revoke permission from user."""
        self.permissions.discard(permission)

    def touch(self, last_seen: Optional[datetime] = None) -> None:
        """Update last seen timestamp."""
        self.last_seen = last_seen or datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_admin': self.is_admin,
            'is_allowed': self.is_allowed,
        }

    def __str__(self) -> str:
        return f"<User {self.user_id}: {self.display_name}>"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class UserSession:
    """User session data."""

    user: User
    context_data: dict = field(default_factory=dict)
    last_action: Optional[str] = None
    last_action_time: Optional[datetime] = None
    conversation_state: dict = field(default_factory=dict)

    def update_action(self, action: str) -> None:
        """Update last action."""
        self.last_action = action
        self.last_action_time = datetime.now()

    def set_state(self, key: str, value) -> None:
        """Set conversation state."""
        self.conversation_state[key] = value

    def get_state(self, key: str, default=None):
        """Get conversation state."""
        return self.conversation_state.get(key, default)

    def clear_state(self) -> None:
        """Clear conversation state."""
        self.conversation_state.clear()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'user': self.user.to_dict(),
            'last_action': self.last_action,
            'last_action_time': self.last_action_time.isoformat() if self.last_action_time else None,
            'conversation_state': self.conversation_state,
        }
