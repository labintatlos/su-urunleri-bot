"""
Species callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.services import SearchService
from bot.formatters import KeyboardFormatter, TextFormatter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class SpeciesHandler(CallbackHandler):
    """Handles species callbacks."""

    def __init__(self):
        """Initialize handler."""
        super().__init__()
        self.search_service = SearchService()

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle species callback."""
        query = update.callback_query
        data = query.data

        if data.startswith('sp:'):
            parts = data.split(':')
            if len(parts) >= 3:
                kind = parts[1]
                species_id = int(parts[2])
                await self.show_species(query, kind, species_id, context)
        elif data == 'species:menu':
            await self.show_species_menu(query)

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return (
            callback_data.startswith('sp:') or
            callback_data == 'species:menu'
        )

    async def show_species_menu(self, query) -> None:
        """Show species menu."""
        text = '🐟 <b>TÜR / BOY / ZAMAN</b>\n\nHangi faaliyet?'

        buttons = [
            [('🎣 Ticari (6/1)', 'species:kind:commercial'),
             ('🎣 Amatör (6/2)', 'species:kind:amateur')],
            [('🎣 Tamamen yasak tür', 'species:kind:prohibited')],
            [('🏠 Ana Menü', 'menu')],
        ]

        keyboard = KeyboardFormatter.inline_keyboard(buttons)
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    async def show_species(
        self,
        query,
        kind: str,
        species_id: int,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Show species details."""
        try:
            species = self.search_service.get_species(kind, species_id)

            if not species:
                await query.answer('Tür bulunamadı!', show_alert=True)
                return

            name = species.get('name', 'Bilinmeyen')
            min_cm = species.get('min_cm')
            min_kg = species.get('min_kg')

            text = f'🐟 <b>{TextFormatter.escape_html(name)}</b>\n'

            if min_cm:
                text += f'📏 Asgari boy: <b>{min_cm} cm</b>\n'
            if min_kg:
                text += f'⚖️ Asgari ağırlık: <b>{min_kg} kg</b>\n'

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
                "Species shown",
                extra={
                    'user_id': query.from_user.id,
                    'species': name,
                    'kind': kind
                }
            )

        except Exception as e:
            logger.error(f"Failed to show species: {e}")
            await query.answer('Tür yüklenemedi!', show_alert=True)
