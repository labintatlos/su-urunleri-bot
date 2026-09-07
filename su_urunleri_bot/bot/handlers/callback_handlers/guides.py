"""
Guide callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.formatters import KeyboardFormatter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class GuideHandler(CallbackHandler):
    """Handles guide callbacks."""

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle guide callback."""
        query = update.callback_query
        data = query.data

        if data == 'guide:menu':
            await self.show_guide_menu(query)

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return callback_data.startswith('guide:')

    async def show_guide_menu(self, query) -> None:
        """Show guide menu."""
        text = (
            '<b>📋 TEKNE TÜRÜ KILAVUZLARI</b>\n\n'
            'Çıkacağınız tekneye özel kontrol föyünü seçin.'
        )

        buttons = [
            [('Örnek Kılavuz 1', 'guide:open:example1')],
            [('🏠 Ana Menü', 'menu')],
        ]

        keyboard = KeyboardFormatter.inline_keyboard(buttons)
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info("Guide menu shown", extra={'user_id': query.from_user.id})
