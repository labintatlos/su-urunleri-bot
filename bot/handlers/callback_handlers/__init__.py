"""
Callback query handlers for menu, articles, species, penalties, guides, audit, and admin.
"""

from bot.handlers.callback_handlers.base import CallbackHandler
from bot.handlers.callback_handlers.router import CallbackRouter, MenuRouter
from bot.handlers.callback_handlers.menu import MenuHandler
from bot.handlers.callback_handlers.articles import ArticleHandler
from bot.handlers.callback_handlers.species import SpeciesHandler
from bot.handlers.callback_handlers.penalties import PenaltyHandler
from bot.handlers.callback_handlers.guides import GuideHandler
from bot.handlers.callback_handlers.audit import AuditHandler
from bot.handlers.callback_handlers.admin import AdminHandler

__all__ = [
    "CallbackHandler",
    "CallbackRouter",
    "MenuRouter",
    "MenuHandler",
    "ArticleHandler",
    "SpeciesHandler",
    "PenaltyHandler",
    "GuideHandler",
    "AuditHandler",
    "AdminHandler",
]
