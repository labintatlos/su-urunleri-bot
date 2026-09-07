"""
Keyboard builders for Telegram inline and reply keyboards.
"""

from typing import List, Tuple, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove


class KeyboardFormatter:
    """Build Telegram keyboards."""

    @staticmethod
    def inline_button(text: str, callback: str) -> InlineKeyboardButton:
        """Create inline button."""
        return InlineKeyboardButton(text, callback_data=callback)

    @staticmethod
    def inline_url_button(text: str, url: str) -> InlineKeyboardButton:
        """Create URL button."""
        return InlineKeyboardButton(text, url=url)

    @staticmethod
    def inline_keyboard(
        buttons: List[List[Tuple[str, str]]],
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard from button grid.

        Args:
            buttons: List of rows, each row is list of (text, callback) tuples
        """
        rows = []
        for row in buttons:
            row_buttons = [
                KeyboardFormatter.inline_button(text, callback)
                for text, callback in row
            ]
            rows.append(row_buttons)
        return InlineKeyboardMarkup(rows)

    @staticmethod
    def menu_keyboard(items: List[Tuple[str, str]], columns: int = 2) -> InlineKeyboardMarkup:
        """Create menu keyboard with items arranged in columns."""
        rows = []
        for i in range(0, len(items), columns):
            row = [
                KeyboardFormatter.inline_button(text, callback)
                for text, callback in items[i:i+columns]
            ]
            rows.append(row)
        return InlineKeyboardMarkup(rows)

    @staticmethod
    def yes_no_keyboard(yes_cb: str = 'yes', no_cb: str = 'no') -> InlineKeyboardMarkup:
        """Create yes/no keyboard."""
        return KeyboardFormatter.inline_keyboard([
            [('✅ Evet', yes_cb), ('❌ Hayır', no_cb)]
        ])

    @staticmethod
    def confirm_cancel_keyboard(
        confirm_cb: str = 'confirm',
        cancel_cb: str = 'cancel',
    ) -> InlineKeyboardMarkup:
        """Create confirm/cancel keyboard."""
        return KeyboardFormatter.inline_keyboard([
            [('✅ Onayla', confirm_cb), ('❌ İptal', cancel_cb)]
        ])

    @staticmethod
    def back_menu_keyboard(back_cb: str = 'menu') -> InlineKeyboardMarkup:
        """Create back to menu keyboard."""
        return KeyboardFormatter.inline_keyboard([
            [('🏠 Ana Menü', back_cb)]
        ])

    @staticmethod
    def pagination_keyboard(
        current_page: int,
        total_pages: int,
        prefix: str = 'page',
    ) -> InlineKeyboardMarkup:
        """Create pagination keyboard."""
        if total_pages <= 1:
            return KeyboardFormatter.inline_keyboard([[('🏠 Ana Menü', 'menu')]])

        buttons = []
        if current_page > 0:
            buttons.append(('◀️ Önceki', f'{prefix}:{current_page-1}'))
        if current_page < total_pages - 1:
            buttons.append(('Sonraki ▶️', f'{prefix}:{current_page+1}'))

        if buttons:
            return KeyboardFormatter.inline_keyboard([buttons])
        return KeyboardFormatter.back_menu_keyboard()

    @staticmethod
    def navigation_keyboard(
        back_cb: str = 'menu',
        extra_buttons: Optional[List[Tuple[str, str]]] = None,
    ) -> InlineKeyboardMarkup:
        """Create navigation keyboard with back button."""
        buttons = extra_buttons or []
        buttons.append(('🏠 Ana Menü', back_cb))
        return KeyboardFormatter.inline_keyboard([[b] for b in buttons])

    @staticmethod
    def search_filter_keyboard(
        filters: List[Tuple[str, str]],
    ) -> InlineKeyboardMarkup:
        """Create filter/search options keyboard."""
        return KeyboardFormatter.menu_keyboard(filters, columns=1)

    @staticmethod
    def reply_keyboard(
        items: List[str],
        columns: int = 2,
        one_time: bool = True,
        selective: bool = False,
    ) -> ReplyKeyboardMarkup:
        """Create reply keyboard."""
        rows = []
        for i in range(0, len(items), columns):
            row = items[i:i+columns]
            rows.append(row)
        return ReplyKeyboardMarkup(
            rows,
            one_time_keyboard=one_time,
            selective=selective,
            resize_keyboard=True,
        )

    @staticmethod
    def remove_keyboard() -> ReplyKeyboardRemove:
        """Remove reply keyboard."""
        return ReplyKeyboardRemove()

    @staticmethod
    def action_keyboard(
        actions: List[Tuple[str, str]],
        columns: int = 2,
    ) -> InlineKeyboardMarkup:
        """Create action buttons keyboard."""
        return KeyboardFormatter.menu_keyboard(actions, columns=columns)

    @staticmethod
    def category_keyboard(
        categories: List[str],
        prefix: str = 'cat',
    ) -> InlineKeyboardMarkup:
        """Create category selector keyboard."""
        buttons = [
            (cat, f'{prefix}:{cat}')
            for cat in categories
        ]
        return KeyboardFormatter.menu_keyboard(buttons, columns=1)

    @staticmethod
    def region_keyboard() -> InlineKeyboardMarkup:
        """Create region selector keyboard."""
        regions = [
            ('Karadeniz', 'audit:region:karadeniz'),
            ('Marmara Denizi', 'audit:region:marmara'),
            ('İstanbul Boğazı', 'audit:region:istanbul'),
            ('Çanakkale Boğazı', 'audit:region:canakkale'),
            ('Ege Denizi', 'audit:region:ege'),
            ('Akdeniz', 'audit:region:akdeniz'),
            ('Uluslararası', 'audit:region:international'),
        ]
        return KeyboardFormatter.menu_keyboard(regions, columns=2)

    @staticmethod
    def activity_keyboard() -> InlineKeyboardMarkup:
        """Create activity type keyboard."""
        activities = [
            ('🎣 Ticari (6/1)', 'audit:activity:commercial'),
            ('🎣 Amatör (6/2)', 'audit:activity:amateur'),
        ]
        return KeyboardFormatter.inline_keyboard([activities])

    @staticmethod
    def subject_keyboard() -> InlineKeyboardMarkup:
        """Create audit subject keyboard."""
        subjects = [
            ('Avcılık faaliyeti', 'audit:subject:fishing'),
            ('Gemi/Ruhsat', 'audit:subject:vessel'),
            ('Ürün/Tür kontrolü', 'audit:subject:species'),
            ('Nakil/Satış kontrolü', 'audit:subject:transport'),
        ]
        return KeyboardFormatter.menu_keyboard(subjects, columns=2)
