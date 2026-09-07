"""
Rate limiting middleware for preventing abuse.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from bot.config import get_config
from bot.exceptions import RateLimitError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """Rate limiting for users."""

    def __init__(self):
        """Initialize rate limiter."""
        self.config = get_config()
        self.user_requests: Dict[int, list] = {}

    def check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit."""
        if not self.config.rate_limit_enabled:
            return True

        now = datetime.now()
        limit = self.config.max_requests_per_minute

        # Get user requests in last minute
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []

        requests = self.user_requests[user_id]

        # Remove old requests outside the window
        cutoff = now - timedelta(minutes=1)
        requests = [req_time for req_time in requests if req_time > cutoff]
        self.user_requests[user_id] = requests

        # Check limit
        if len(requests) >= limit:
            logger.warning(
                "Rate limit exceeded",
                extra={'user_id': user_id, 'requests': len(requests)}
            )
            return False

        return True

    def record_request(self, user_id: int) -> None:
        """Record a user request."""
        if not self.config.rate_limit_enabled:
            return

        if user_id not in self.user_requests:
            self.user_requests[user_id] = []

        now = datetime.now()
        self.user_requests[user_id].append(now)

        logger.debug(
            "Request recorded",
            extra={'user_id': user_id}
        )

    def require_rate_limit(self, user_id: int) -> None:
        """Require rate limit check, raise if exceeded."""
        if not self.check_rate_limit(user_id):
            raise RateLimitError(
                f"User {user_id} has exceeded rate limit"
            )

        self.record_request(user_id)

    def get_reset_time(self, user_id: int) -> Optional[datetime]:
        """Get when rate limit resets for user."""
        if not self.config.rate_limit_enabled:
            return None

        if user_id not in self.user_requests:
            return None

        requests = self.user_requests[user_id]
        if not requests:
            return None

        oldest = min(requests)
        reset_time = oldest + timedelta(minutes=1)
        return reset_time

    def get_remaining_time(self, user_id: int) -> Optional[int]:
        """Get seconds until rate limit resets."""
        reset_time = self.get_reset_time(user_id)
        if not reset_time:
            return None

        now = datetime.now()
        remaining = (reset_time - now).total_seconds()
        return max(0, int(remaining))

    def get_user_request_count(self, user_id: int) -> int:
        """Get current request count for user."""
        if user_id not in self.user_requests:
            return 0

        now = datetime.now()
        requests = self.user_requests[user_id]

        # Clean old requests
        cutoff = now - timedelta(minutes=1)
        requests = [r for r in requests if r > cutoff]
        self.user_requests[user_id] = requests

        return len(requests)

    def clear_user_requests(self, user_id: int) -> None:
        """Clear all requests for a user."""
        if user_id in self.user_requests:
            del self.user_requests[user_id]
            logger.debug("User requests cleared", extra={'user_id': user_id})

    def cleanup_old_requests(self) -> None:
        """Clean up requests older than 1 hour."""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)

        users_to_clean = []
        for user_id, requests in self.user_requests.items():
            requests = [r for r in requests if r > cutoff]
            if requests:
                self.user_requests[user_id] = requests
            else:
                users_to_clean.append(user_id)

        for user_id in users_to_clean:
            del self.user_requests[user_id]

        if users_to_clean:
            logger.debug(f"Cleaned up {len(users_to_clean)} users")


# Global rate limiter instance
_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_rate_limiter() -> None:
    """Reset the global rate limiter (useful for testing)."""
    global _limiter
    _limiter = None
