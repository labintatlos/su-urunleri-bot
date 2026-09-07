"""
Text formatting utilities for messages and UI.
"""

import html
from typing import Optional, List, Dict


class TextFormatter:
    """Utilities for text formatting."""

    @staticmethod
    def escape_html(text: str) -> str:
        """HTML escape text for Telegram."""
        return html.escape(str(text or ''))

    @staticmethod
    def safe_text(text: Optional[str]) -> str:
        """Get safe text or dash."""
        if not text:
            return '—'
        return TextFormatter.escape_html(text)

    @staticmethod
    def format_number(value: float, decimals: int = 0) -> str:
        """Format number with Turkish locale."""
        if value is None:
            return '—'
        format_str = f'{{:,.{decimals}f}}'
        formatted = format_str.format(float(value))
        return formatted.replace(',', '.')

    @staticmethod
    def format_money(value: float) -> str:
        """Format money amount."""
        if value is None:
            return '—'
        return f"{TextFormatter.format_number(value, 0)} TL"

    @staticmethod
    def format_percent(value: float, decimals: int = 1) -> str:
        """Format percentage."""
        if value is None:
            return '—'
        return f"{TextFormatter.format_number(value, decimals)}%"

    @staticmethod
    def bold(text: str) -> str:
        """Make text bold."""
        return f"<b>{TextFormatter.escape_html(text)}</b>"

    @staticmethod
    def italic(text: str) -> str:
        """Make text italic."""
        return f"<i>{TextFormatter.escape_html(text)}</i>"

    @staticmethod
    def code(text: str) -> str:
        """Format text as code."""
        return f"<code>{TextFormatter.escape_html(text)}</code>"

    @staticmethod
    def join_lines(lines: List[str], separator: str = '\n') -> str:
        """Join lines with separator."""
        return separator.join(str(line) for line in lines if line)

    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = '...') -> str:
        """Truncate text to max length."""
        text = str(text or '')
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 4000) -> List[str]:
        """Split text into chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        lines = text.split('\n')
        current_chunk = ''

        for line in lines:
            if len(current_chunk) + len(line) + 1 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'

        if current_chunk:
            chunks.append(current_chunk.rstrip('\n'))

        return chunks

    @staticmethod
    def format_list(items: List[str], ordered: bool = False) -> str:
        """Format list of items."""
        lines = []
        for i, item in enumerate(items, 1):
            prefix = f"{i}." if ordered else "▪️"
            lines.append(f"{prefix} {item}")
        return TextFormatter.join_lines(lines)

    @staticmethod
    def format_table(headers: List[str], rows: List[List[str]]) -> str:
        """Format simple table."""
        if not headers or not rows:
            return ''

        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        lines = []
        header_line = ' | '.join(
            str(h).ljust(w) for h, w in zip(headers, col_widths)
        )
        lines.append(header_line)
        lines.append('-' * len(header_line))

        for row in rows:
            row_line = ' | '.join(
                str(cell).ljust(w) for cell, w in zip(row, col_widths)
            )
            lines.append(row_line)

        return TextFormatter.join_lines(lines)

    @staticmethod
    def format_section(title: str, content: str) -> str:
        """Format a section with title."""
        lines = [
            f"<b>{TextFormatter.escape_html(title)}</b>",
            TextFormatter.escape_html(content),
        ]
        return TextFormatter.join_lines(lines, '\n')

    @staticmethod
    def format_details(data: Dict[str, str]) -> str:
        """Format key-value details."""
        lines = []
        for key, value in data.items():
            lines.append(f"<b>{TextFormatter.escape_html(key)}:</b> {TextFormatter.escape_html(value)}")
        return TextFormatter.join_lines(lines)

    @staticmethod
    def add_emoji(text: str, emoji: str) -> str:
        """Add emoji prefix to text."""
        return f"{emoji} {text}"

    @staticmethod
    def format_timestamp(dt, format_str: str = '%d.%m.%Y %H:%M') -> str:
        """Format datetime."""
        if dt is None:
            return '—'
        try:
            return dt.strftime(format_str)
        except Exception:
            return '—'
