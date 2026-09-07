"""
Admin panel callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.middleware import get_auth
from bot.services import AdminService
from bot.formatters import KeyboardFormatter, MessageFormatter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class AdminHandler(CallbackHandler):
    """Handles admin callbacks."""

    def __init__(self):
        """Initialize handler."""
        super().__init__()
        self.admin_service = AdminService()

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin callback."""
        query = update.callback_query
        user_id = query.from_user.id

        # Check admin permission
        if not self.auth.check_admin(user_id):
            await query.answer('Yönetici yetkiniz yok!', show_alert=True)
            return

        data = query.data

        if data == 'admin:panel':
            await self.show_admin_panel(query)
        elif data.startswith('admin:stats:'):
            section = data.split(':')[2]
            await self.show_stats(query, section)

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return callback_data.startswith('admin:')

    async def show_admin_panel(self, query) -> None:
        """Show admin panel."""
        text = (
            '<b>🔐 YÖNETİCİ PANELİ</b>\n\n'
            'Hoş geldiniz yönetici!'
        )

        buttons = [
            [('📊 İstatistikler', 'admin:stats:main')],
            [('👥 Kullanıcılar', 'admin:stats:users')],
            [('🔍 Son Sorgular', 'admin:stats:logs')],
            [('🏠 Ana Menü', 'menu')],
        ]

        keyboard = KeyboardFormatter.inline_keyboard(buttons)
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info("Admin panel shown", extra={'user_id': query.from_user.id})

    async def show_stats(self, query, section: str) -> None:
        """Show statistics."""
        try:
            if section == 'main':
                report = self.admin_service.format_stats_report()
            elif section == 'users':
                report = '<b>👥 Kullanıcı İstatistikleri</b>\n\nKullanıcı verisi yükleniyor...'
            elif section == 'logs':
                report = '<b>🔍 Son Sorgular</b>\n\nSon sorgular yükleniyor...'
            else:
                report = '<b>İstatistikler</b>\n\nBilgi yükleniyor...'

            buttons = [
                [('🔙 Yönetici Paneli', 'admin:panel')],
                [('🏠 Ana Menü', 'menu')],
            ]

            keyboard = KeyboardFormatter.inline_keyboard(buttons)
            await query.edit_message_text(
                text=report,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

            logger.info(
                "Stats shown",
                extra={'user_id': query.from_user.id, 'section': section}
            )

        except Exception as e:
            logger.error(f"Failed to show stats: {e}")
            await query.answer('İstatistikler yüklenemedi!', show_alert=True)
