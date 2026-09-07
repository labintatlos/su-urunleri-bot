"""
Base text handler class.
"""

from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes

from bot.middleware import get_auth, get_rate_limiter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class TextHandler(ABC):
    """Base class for text handlers."""

    def __init__(self):
        """Initialize handler."""
        self.auth = get_auth()
        self.rate_limiter = get_rate_limiter()

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text message."""
        user = update.effective_user

        # Check auth
        if not self.auth.check_user_allowed(user.id, user.username):
            return

        # Check rate limit
        try:
            self.rate_limiter.require_rate_limit(user.id)
        except Exception:
            logger.warning("Rate limit exceeded", extra={'user_id': user.id})
            return

        # Handle text
        try:
            await self.handle_text(update, context)
        except Exception as e:
            logger.error(f"Text handler error: {e}", extra={'user_id': user.id})

    @abstractmethod
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the text. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def can_handle(self, mode: str, text: str) -> bool:
        """Check if this handler can handle the text."""
        pass
