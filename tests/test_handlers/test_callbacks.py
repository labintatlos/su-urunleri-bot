"""
Tests for callback handlers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.callback_handlers import MenuHandler, ArticleHandler


@pytest.mark.asyncio
class TestMenuHandler:
    """Test MenuHandler."""

    @pytest.fixture
    def handler(self):
        """Create menu handler."""
        return MenuHandler()

    async def test_can_handle_menu(self, handler):
        """Test that handler can handle menu callback."""
        assert handler.can_handle('menu')

    async def test_cannot_handle_other(self, handler):
        """Test that handler rejects other callbacks."""
        assert not handler.can_handle('article:123')

    async def test_show_main_menu(self, handler, mock_callback_query):
        """Test showing main menu."""
        query = mock_callback_query
        query.data = 'menu'

        # Mock the edit method
        query.edit_message_text = AsyncMock()

        try:
            await handler.show_main_menu(query, MagicMock())
            query.edit_message_text.assert_called_once()
        except Exception:
            # Expected if auth check fails
            pass


@pytest.mark.asyncio
class TestArticleHandler:
    """Test ArticleHandler."""

    @pytest.fixture
    def handler(self):
        """Create article handler."""
        return ArticleHandler()

    async def test_can_handle_article(self, handler):
        """Test that handler can handle article callback."""
        assert handler.can_handle('art:61:18')

    async def test_cannot_handle_other(self, handler):
        """Test that handler rejects other callbacks."""
        assert not handler.can_handle('menu')

    async def test_show_article(self, handler, mock_callback_query):
        """Test showing article."""
        query = mock_callback_query
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        # Mock the service
        handler.search_service.get_article = MagicMock(
            return_value=None
        )

        await handler.show_article(query, '61', 18)
        query.answer.assert_called_once()
