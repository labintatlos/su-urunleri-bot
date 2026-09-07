"""
Penalty card callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.services import SearchService, PenaltyService
from bot.formatters import KeyboardFormatter, TextFormatter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class PenaltyHandler(CallbackHandler):
    """Handles penalty callbacks."""

    def __init__(self):
        """Initialize handler."""
        super().__init__()
        self.search_service = SearchService()
        self.penalty_service = PenaltyService()

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle penalty callback."""
        query = update.callback_query
        data = query.data

        if data.startswith('pen:'):
            penalty_id = int(data.split(':')[1])
            await self.show_penalty(query, penalty_id)

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return callback_data.startswith('pen:')

    async def show_penalty(self, query, penalty_id: int) -> None:
        """Show penalty card."""
        try:
            penalty = self.search_service.get_penalty(penalty_id)

            if not penalty:
                await query.answer('Ceza kartı bulunamadı!', show_alert=True)
                return

            violation = penalty.get('violation', '?')
            option = penalty.get('option_text', '')
            base_amount = penalty.get('base_ipc', 0)

            text = (
                f'⚖️ <b>{TextFormatter.escape_html(violation)}</b>\n'
                f'Seçenek: {TextFormatter.escape_html(option)}\n'
            )

            if base_amount:
                text += f'💰 Taban Ceza: {base_amount:,.0f} TL\n'

            buttons = [
                ('🏠 Ana Menü', 'menu'),
            ]
            keyboard = KeyboardFormatter.inline_keyboard([buttons])

            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

            logger.info(
                "Penalty shown",
                extra={'user_id': query.from_user.id, 'penalty_id': penalty_id}
            )

        except Exception as e:
            logger.error(f"Failed to show penalty: {e}")
            await query.answer('Ceza kartı yüklenemedi!', show_alert=True)
