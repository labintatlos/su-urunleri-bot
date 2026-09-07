"""
Article display callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.services import SearchService
from bot.formatters import KeyboardFormatter, TextFormatter
from bot.logger import setup_logger

logger = setup_logger(__name__)


class ArticleHandler(CallbackHandler):
    """Handles article display callbacks."""

    def __init__(self):
        """Initialize handler."""
        super().__init__()
        self.search_service = SearchService()

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle article callback."""
        query = update.callback_query
        data = query.data

        if data.startswith('art:'):
            parts = data.split(':')
            if len(parts) == 3:
                source, article = parts[1], parts[2]
                await self.show_article(query, source, int(article))

    def can_handle(self, callback_data: str) -> bool:
        """Check if this handler can handle the callback."""
        return callback_data.startswith('art:')

    async def show_article(self, query, source: str, article: int) -> None:
        """Show article."""
        try:
            article_data = self.search_service.get_article(source, article)

            if not article_data:
                await query.answer('Madde bulunamadı!', show_alert=True)
                return

            # Format article text
            title = article_data.get('title', f'Madde {article}')
            body = article_data.get('body', 'İçerik yok.')
            page_start = article_data.get('page_start', '?')
            page_end = article_data.get('page_end', '?')

            text = (
                f'📚 <b>Madde {article}</b>\n'
                f'<b>{TextFormatter.escape_html(title)}</b>\n'
                f'<i>Sayfa {page_start}-{page_end}</i>\n\n'
                f'{TextFormatter.escape_html(body[:1000])}'
            )

            # Keyboard
            buttons = [
                ('⭐ Favoriye Ekle', f'fav:add:article:{source}-{article}'),
                ('🏠 Ana Menü', 'menu'),
            ]
            keyboard = KeyboardFormatter.inline_keyboard([buttons])

            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

            logger.info(
                "Article shown",
                extra={
                    'user_id': query.from_user.id,
                    'source': source,
                    'article': article
                }
            )

        except Exception as e:
            logger.error(f"Failed to show article: {e}")
            await query.answer('Madde yüklenemedi!', show_alert=True)
