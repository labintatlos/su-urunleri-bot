"""
Menu navigation callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.formatters import KeyboardFormatter, MessageFormatter
from bot.middleware import get_auth
from bot.logger import setup_logger

logger = setup_logger(__name__)


class MenuHandler(CallbackHandler):
    """Handles menu navigation callbacks."""

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle menu callback."""
        query = update.callback_query
        data = query.data

        if data == 'menu':
            await self.show_main_menu(query, context)
        elif data.startswith('field:'):
            category = data.split(':', 1)[1]
            await self.show_field_menu(query, category)

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return (
            callback_data == 'menu' or
            callback_data.startswith('field:')
        )

    async def show_main_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show main menu."""
        user_id = query.from_user.id

        menu_buttons = [
            ('📋 Tekne Türü Kılavuzları', 'guide:menu'),
            ('🚨 Denetime Başla', 'audit:start'),
            ('📖 Pratik Ceza Rehberi', 'ceza:menu'),
            ('📖 Pratik Tür Çizelgesi', 'turcizelge:menu'),
            ('🚢 Gemi / Ruhsat / BAGİS', 'vessel:menu'),
            ('🧾 Kolluk İşlem Rehberi', 'field:Kolluk İşlemi'),
            ('🧮 Hesaplayıcılar', 'calc:menu'),
            ('⭐ Favoriler', 'fav:list'),
            ('🕘 Son Sorgular', 'history'),
            ('ℹ️ Sürüm', 'about'),
        ]

        # Add admin panel for admins
        auth = get_auth()
        if auth.check_admin(user_id):
            menu_buttons.append(('🔐 Yönetici Paneli', 'admin:panel'))

        keyboard = KeyboardFormatter.menu_keyboard(menu_buttons, columns=2)

        text = (
            '<b>⚓ SU ÜRÜNLERİ KOLLUK ASİSTANI</b>\n\n'
            '🌊 <b>Deniz görev alanı</b>\n\n'
            'Su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesi, ihlallerin tespiti '
            've uygulanacak işlemlerin belirlenmesine yardımcı olur.'
        )

        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info("Main menu shown", extra={'user_id': user_id})

    async def show_field_menu(self, query, category: str) -> None:
        """Show field (kontrol kartı) menu."""
        # This would load rules from database based on category
        # For now, a placeholder

        text = f'<b>🛡️ {category}</b>\n\nKontrol kartları yükleniyor...'

        keyboard = KeyboardFormatter.inline_keyboard([
            [('🏠 Ana Menü', 'menu')]
        ])

        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info("Field menu shown", extra={'category': category})
