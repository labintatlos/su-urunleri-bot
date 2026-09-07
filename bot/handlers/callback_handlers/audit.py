"""
Audit callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.models import Region, Activity
from bot.formatters import KeyboardFormatter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class AuditHandler(CallbackHandler):
    """Handles audit callbacks."""

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle audit callback."""
        query = update.callback_query
        data = query.data

        if data == 'audit:start':
            await self.start_audit(query, context)
        elif data.startswith('audit:region:'):
            region = data.split(':')[2]
            context.user_data['audit_region'] = region
            await self.choose_activity(query, context)

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return callback_data.startswith('audit:')

    async def start_audit(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start audit process."""
        text = '📍 <b>BÖLGE SEÇİN</b>'

        buttons = [
            [('Karadeniz', 'audit:region:karadeniz'),
             ('Marmara Denizi', 'audit:region:marmara')],
            [('İstanbul Boğazı', 'audit:region:istanbul'),
             ('Çanakkale Boğazı', 'audit:region:canakkale')],
            [('Ege Denizi', 'audit:region:ege'),
             ('Akdeniz', 'audit:region:akdeniz')],
            [('Uluslararası', 'audit:region:international')],
            [('🏠 Ana Menü', 'menu')],
        ]

        keyboard = KeyboardFormatter.inline_keyboard(buttons)
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info("Audit started", extra={'user_id': query.from_user.id})

    async def choose_activity(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Choose activity type."""
        text = '🎣 <b>FAAlİYET TİPİ</b>'

        buttons = [
            [('Ticari (6/1)', 'audit:activity:commercial'),
             ('Amatör (6/2)', 'audit:activity:amateur')],
            [('↩️ Geri', 'audit:start')],
        ]

        keyboard = KeyboardFormatter.inline_keyboard(buttons)
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
