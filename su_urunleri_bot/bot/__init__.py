"""
Su Ürünleri Denetim Asistanı - Telegram Bot
Enhanced version with modular architecture
"""

__version__ = "5.0.0"
__author__ = "Su Ürünleri Collective"

from bot.exceptions import (
    BotException,
    AuthenticationError,
    ValidationError,
    DatabaseError,
    TelegramError,
    RateLimitError,
)

from bot.config import Config
from bot.logger import setup_logger

__all__ = [
    "Config",
    "setup_logger",
    "BotException",
    "AuthenticationError",
    "ValidationError",
    "DatabaseError",
    "TelegramError",
    "RateLimitError",
]
