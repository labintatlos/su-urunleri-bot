"""
Callback router - dispatches callbacks to appropriate handlers.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.logger import setup_logger

logger = setup_logger(__name__)


class CallbackRouter:
    """Routes callback queries to appropriate handlers."""

    def __init__(self):
        """Initialize router."""
        self.handlers = {}

    def register(self, prefix: str, handler) -> None:
        """Register a handler for a callback prefix."""
        self.handlers[prefix] = handler
        logger.debug(f"Registered handler for prefix: {prefix}")

    async def route(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route callback to appropriate handler."""
        query = update.callback_query
        callback_data = query.data

        # Find matching handler
        for prefix, handler in self.handlers.items():
            if callback_data.startswith(prefix):
                logger.debug(
                    "Routing callback",
                    extra={'prefix': prefix, 'data': callback_data}
                )
                await handler.handle(update, context)
                return

        logger.warning(
            "No handler found for callback",
            extra={'data': callback_data}
        )
        await query.answer('İşlem bulunamadı!', show_alert=True)


class MenuRouter:
    """Routes menu-related callbacks."""

    @staticmethod
    async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle menu callback."""
        query = update.callback_query
        data = query.data

        if data == 'menu':
            # Show main menu
            logger.debug("Menu callback triggered")
            # This would trigger the main menu display
            # Implementation depends on specific menu logic

        await query.answer()
