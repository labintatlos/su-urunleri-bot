"""
Custom exceptions for the bot application.
Provides a hierarchy of exceptions for different error scenarios.
"""


class BotException(Exception):
    """Base exception for all bot-related errors."""
    pass


class AuthenticationError(BotException):
    """Raised when user authentication fails."""
    pass


class AuthorizationError(BotException):
    """Raised when user lacks required permissions."""
    pass


class ValidationError(BotException):
    """Raised when input validation fails."""
    pass


class DatabaseError(BotException):
    """Raised when database operations fail."""
    pass


class MigrationError(DatabaseError):
    """Raised when database migration fails."""
    pass


class QueryError(DatabaseError):
    """Raised when a database query fails."""
    pass


class TelegramError(BotException):
    """Raised when Telegram API operations fail."""
    pass


class TelegramSendError(TelegramError):
    """Raised when message sending fails."""
    pass


class ConfigurationError(BotException):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(BotException):
    """Raised when rate limit is exceeded."""
    pass


class NotFoundError(BotException):
    """Raised when a requested resource is not found."""
    pass


class ServiceError(BotException):
    """Raised when a service operation fails."""
    pass


class AuditError(ServiceError):
    """Raised when audit-related operations fail."""
    pass


class SearchError(ServiceError):
    """Raised when search operations fail."""
    pass
