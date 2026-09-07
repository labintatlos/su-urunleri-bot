"""
Structured logging configuration for the bot.
Provides comprehensive logging with proper formatting, rotation, and context.
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict

from bot.config import get_config


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with context information."""
        log_obj: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add extra context fields
        if hasattr(record, 'user_id'):
            log_obj['user_id'] = record.user_id
        if hasattr(record, 'username'):
            log_obj['username'] = record.username
        if hasattr(record, 'action'):
            log_obj['action'] = record.action
        if hasattr(record, 'query'):
            log_obj['query'] = record.query
        if hasattr(record, 'duration_ms'):
            log_obj['duration_ms'] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
            log_obj['exc_type'] = record.exc_info[0].__name__

        return json.dumps(log_obj, ensure_ascii=False)


class SimpleFormatter(logging.Formatter):
    """Simple text formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color coding."""
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        msg = record.getMessage()

        # Add user context if available
        context = ''
        if hasattr(record, 'user_id'):
            context = f' [uid={record.user_id}]'

        # Format exception
        exc = ''
        if record.exc_info:
            exc = f'\n{self.formatException(record.exc_info)}'

        return f'{timestamp} {color}[{record.levelname}]{reset} {record.name}: {msg}{context}{exc}'


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a logger instance with file and console handlers.

    Args:
        name: Logger name (defaults to module name)

    Returns:
        Configured logger instance
    """
    config = get_config()
    logger = logging.getLogger(name or __name__)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set log level
    log_level = getattr(logging, config.log_level)
    logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(SimpleFormatter())
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = config.logs_path / 'bot.log'
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Critical errors to separate file
    critical_file = config.logs_path / 'critical.log'
    critical_handler = logging.handlers.RotatingFileHandler(
        filename=critical_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(JSONFormatter())
    logger.addHandler(critical_handler)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    action: Optional[str] = None,
    query: Optional[str] = None,
    duration_ms: Optional[float] = None,
    **extra
) -> None:
    """
    Log a message with context information.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        user_id: Telegram user ID
        username: Username
        action: Action being performed
        query: Search query or input
        duration_ms: Operation duration in milliseconds
        **extra: Additional context fields
    """
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )

    # Add context
    if user_id is not None:
        record.user_id = user_id
    if username is not None:
        record.username = username
    if action is not None:
        record.action = action
    if query is not None:
        record.query = query
    if duration_ms is not None:
        record.duration_ms = f"{duration_ms:.2f}ms"

    # Add extra fields
    for key, value in extra.items():
        setattr(record, key, value)

    logger.handle(record)


# Convenience functions
def debug(logger: logging.Logger, msg: str, **kwargs) -> None:
    """Log debug message with context."""
    log_with_context(logger, logging.DEBUG, msg, **kwargs)


def info(logger: logging.Logger, msg: str, **kwargs) -> None:
    """Log info message with context."""
    log_with_context(logger, logging.INFO, msg, **kwargs)


def warning(logger: logging.Logger, msg: str, **kwargs) -> None:
    """Log warning message with context."""
    log_with_context(logger, logging.WARNING, msg, **kwargs)


def error(logger: logging.Logger, msg: str, **kwargs) -> None:
    """Log error message with context."""
    log_with_context(logger, logging.ERROR, msg, **kwargs)


def critical(logger: logging.Logger, msg: str, **kwargs) -> None:
    """Log critical message with context."""
    log_with_context(logger, logging.CRITICAL, msg, **kwargs)
