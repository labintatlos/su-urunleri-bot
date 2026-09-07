"""
Base callback handler class.
"""

from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes

from bot.middleware import get_auth, get_rate_limiter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class CallbackHandler(ABC):
    """Base class for callback handlers."""

    def __init__(self):
        """Initialize handler."""
        self.auth = get_auth()
        self.rate_limiter = get_rate_limiter()

    async def check_auth(self, update: Update) -> bool:
        """Check if user is authorized."""
        user = update.effective_user
        if not self.auth.check_user_allowed(user.id, user.username):
            logger.warning(
                "Unauthorized callback",
                extra={'user_id': user.id, 'callback': update.callback_query.data}
            )
            return False
        return True

    async def check_rate_limit(self, update: Update) -> bool:
        """Check rate limit."""
        user = update.effective_user
        try:
            self.rate_limiter.require_rate_limit(user.id)
            return True
        except Exception:
            logger.warning("Rate limit exceeded", extra={'user_id': user.id})
            return False

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback query."""
        # Check auth
        if not await self.check_auth(update):
            await update.callback_query.answer('Yetkiniz yok!', show_alert=True)
            return

        # Check rate limit
        if not await self.check_rate_limit(update):
            await update.callback_query.answer('Çok sık talep gönderdiniz!', show_alert=True)
            return

        # Handle callback
        try:
            await self.handle_callback(update, context)
            await update.callback_query.answer()
        except Exception as e:
            logger.error(
                f"Callback handler error: {e}",
                extra={'user_id': update.effective_user.id}
            )
            await update.callback_query.answer('Hata oluştu!', show_alert=True)

    @abstractmethod
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the callback. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        pass
