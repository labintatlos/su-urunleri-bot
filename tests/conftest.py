"""
Pytest configuration and fixtures for bot tests.
Provides mocking, database fixtures, and test data.
"""

import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock bot configuration before importing bot modules
@pytest.fixture(scope='session', autouse=True)
def mock_config():
    """Mock configuration to avoid loading actual config."""
    with patch('bot.config.Config') as mock:
        mock.return_value.bot_token = 'TEST_TOKEN'
        mock.return_value.admin_ids = {123456789}
        mock.return_value.allowed_user_ids = set()
        mock.return_value.result_limit = 8
        mock.return_value.timezone = None
        mock.return_value.log_level = 'DEBUG'
        mock.return_value.db_path = Path(':memory:')
        mock.return_value.data_path = Path(__file__).parent.parent / 'data'
        mock.return_value.logs_path = Path(tempfile.gettempdir())
        yield mock


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def async_context():
    """Fixture for async context in tests."""
    yield
    # Cleanup if needed


# Telegram mocking fixtures

@pytest.fixture
def mock_user():
    """Create a mock Telegram user."""
    user = MagicMock()
    user.id = 123456789
    user.first_name = 'Test'
    user.last_name = 'User'
    user.full_name = 'Test User'
    user.username = 'testuser'
    return user


@pytest.fixture
def mock_chat():
    """Create a mock Telegram chat."""
    chat = MagicMock()
    chat.id = 123456789
    chat.type = 'private'
    return chat


@pytest.fixture
def mock_message():
    """Create a mock Telegram message."""
    message = MagicMock()
    message.message_id = 1
    message.chat_id = 123456789
    message.from_user = MagicMock(id=123456789)
    message.text = '/start'
    message.date = None
    message.delete = AsyncMock()
    message.edit_text = AsyncMock()
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_user, mock_chat, mock_message):
    """Create a mock Telegram Update."""
    update = MagicMock()
    update.update_id = 1
    update.effective_user = mock_user
    update.effective_chat = mock_chat
    update.effective_message = mock_message
    update.callback_query = None
    update.message = mock_message
    return update


@pytest.fixture
def mock_callback_query(mock_user, mock_message):
    """Create a mock callback query."""
    query = MagicMock()
    query.id = 'callback_1'
    query.from_user = mock_user
    query.message = mock_message
    query.data = 'test:data'
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_context():
    """Create a mock Telegram context."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.delete_message = AsyncMock()
    context.bot.get_me = AsyncMock(return_value=MagicMock(username='testbot'))
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    context.error = None
    return context


@pytest.fixture
def mock_application():
    """Create a mock Telegram Application."""
    app = AsyncMock()
    app.bot = MagicMock()
    app.bot.send_message = AsyncMock()
    app.bot.get_me = AsyncMock(return_value=MagicMock(username='testbot'))
    return app


# Database fixtures

@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
def in_memory_db() -> Generator[sqlite3.Connection, None, None]:
    """Create an in-memory SQLite database."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def sample_db_schema(in_memory_db: sqlite3.Connection) -> sqlite3.Connection:
    """Create sample database schema for testing."""
    cursor = in_memory_db.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_seen TEXT
        )
    ''')

    # Query log table
    cursor.execute('''
        CREATE TABLE query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            query TEXT,
            created_at TEXT
        )
    ''')

    # Articles table
    cursor.execute('''
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            article INTEGER,
            title TEXT,
            body TEXT,
            page_start INTEGER,
            page_end INTEGER,
            scope TEXT,
            search_text TEXT
        )
    ''')

    # Penalty cards table
    cursor.execute('''
        CREATE TABLE penalty_cards (
            id INTEGER PRIMARY KEY,
            source_row INTEGER,
            violation TEXT,
            option_text TEXT,
            law TEXT,
            regulation TEXT,
            teblig TEXT,
            art36 TEXT,
            base_ipc REAL,
            amounts TEXT,
            product_seizure TEXT,
            means_seizure TEXT,
            repeat_text TEXT,
            license_action TEXT,
            notes TEXT,
            scope TEXT,
            layout TEXT,
            teblig_source TEXT,
            search_text TEXT
        )
    ''')

    # Species tables
    cursor.execute('''
        CREATE TABLE commercial_species (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            min_cm REAL,
            min_kg REAL,
            time_bans TEXT,
            article_time INTEGER,
            search_text TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE amateur_species (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            min_cm REAL,
            min_kg REAL,
            limit_text TEXT,
            time_bans TEXT,
            search_text TEXT
        )
    ''')

    # Favorites table
    cursor.execute('''
        CREATE TABLE favorites (
            user_id INTEGER,
            item_type TEXT,
            item_id TEXT,
            created_at TEXT,
            PRIMARY KEY(user_id, item_type, item_id)
        )
    ''')

    in_memory_db.commit()
    return in_memory_db


# Test data fixtures

@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {
        'user_id': 123456789,
        'username': 'testuser',
        'first_name': 'Test',
        'last_seen': '2024-01-01T12:00:00'
    }


@pytest.fixture
def sample_article_data() -> dict:
    """Sample article data for testing."""
    return {
        'source': '61',
        'article': 18,
        'title': 'Test Article',
        'body': 'This is a test article about fishing regulations.',
        'page_start': 10,
        'page_end': 10,
        'scope': 'sea_or_general',
        'search_text': 'test article fishing'
    }


@pytest.fixture
def sample_species_data() -> dict:
    """Sample species data for testing."""
    return {
        'name': 'Hamsi',
        'min_cm': 9.0,
        'min_kg': None,
        'time_bans': json.dumps(['01-01/06-30']),
        'article_time': None,
        'search_text': 'hamsi'
    }


@pytest.fixture
def sample_penalty_data() -> dict:
    """Sample penalty card data for testing."""
    return {
        'id': 1,
        'source_row': 1,
        'violation': 'Unlicensed fishing',
        'option_text': 'Fishing without license',
        'law': '1380 Kanun Md. 36',
        'regulation': None,
        'teblig': None,
        'art36': 'Para cezası',
        'base_ipc': 5000.0,
        'amounts': json.dumps({'first': 5000, 'repeat': 10000}),
        'product_seizure': 'Evet',
        'means_seizure': 'Evet',
        'repeat_text': 'İkinci ihlalde ceza iki katına çıkar',
        'license_action': 'Geçici ruhsat askısı',
        'notes': 'Test penalty',
        'scope': 'sea_or_general',
        'layout': 'general',
        'teblig_source': None,
        'search_text': 'unlicensed fishing'
    }


# Pytest marks for test categorization

def pytest_configure(config):
    """Register custom pytest marks."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "handler: Handler tests")
    config.addinivalue_line("markers", "db: Database tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "async: Async tests")
