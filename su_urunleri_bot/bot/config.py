"""
Configuration management for the bot application.
Handles loading settings from environment variables, Home Assistant options.json,
and command-line arguments with validation.
"""

import json
import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Optional, Set, Dict, List

from bot.exceptions import ConfigurationError


class Config:
    """Configuration manager with support for multiple sources."""

    # Paths for different deployment contexts
    _HA_OPTIONS = Path('/data/options.json')
    _LOCAL_OPTIONS = Path('./options.json')
    _ENV_PREFIX = 'BOT_'

    def __init__(self):
        """Initialize configuration from environment, options.json, or defaults."""
        self._options: Dict = {}
        self._load_options()
        self._validate()

    def _load_options(self) -> None:
        """Load options from available sources in priority order."""
        # 1. Try Home Assistant options.json
        if self._HA_OPTIONS.exists():
            try:
                with open(self._HA_OPTIONS, 'r', encoding='utf-8') as f:
                    self._options = json.load(f)
                return
            except Exception as e:
                raise ConfigurationError(f"Failed to load Home Assistant options: {e}")

        # 2. Try local options.json
        if self._LOCAL_OPTIONS.exists():
            try:
                with open(self._LOCAL_OPTIONS, 'r', encoding='utf-8') as f:
                    self._options = json.load(f)
                return
            except Exception as e:
                raise ConfigurationError(f"Failed to load local options.json: {e}")

        # 3. Fall back to environment variables
        self._options = {}

    def _get(self, key: str, default=None):
        """Get configuration value with environment variable override."""
        env_key = f'{self._ENV_PREFIX}{key.upper()}'
        if env_key in os.environ:
            return os.environ[env_key]
        return self._options.get(key, default)

    def _validate(self) -> None:
        """Validate critical configuration values."""
        if not self.bot_token:
            raise ConfigurationError(
                "TELEGRAM_TOKEN not found. Set via environment variable or options.json"
            )

    @property
    def bot_token(self) -> str:
        """Telegram bot token (required)."""
        token = self._get('bot_token') or os.environ.get('TELEGRAM_TOKEN', '')
        if not token:
            raise ConfigurationError("bot_token is required")
        return token.strip()

    @property
    def admin_ids(self) -> Set[int]:
        """Set of admin user IDs."""
        value = self._get('admin_id', '')
        return self._parse_ids(value)

    @property
    def allowed_user_ids(self) -> Set[int]:
        """Set of allowed user IDs."""
        value = self._get('allowed_users', [])
        user_ids = set()

        if isinstance(value, list):
            for entry in value:
                user_ids.update(self._parse_ids(entry))
        elif isinstance(value, str):
            user_ids = self._parse_ids(value)

        return user_ids

    @property
    def result_limit(self) -> int:
        """Maximum results per search query."""
        try:
            limit = int(self._get('result_limit', 8))
            return max(1, min(limit, 20))  # Clamp between 1-20
        except (ValueError, TypeError):
            return 8

    @property
    def timezone(self) -> ZoneInfo:
        """Timezone for timestamps."""
        tz_str = self._get('timezone', 'Europe/Istanbul')
        try:
            return ZoneInfo(tz_str)
        except Exception:
            return ZoneInfo('Europe/Istanbul')

    @property
    def log_level(self) -> str:
        """Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
        level = (self._get('log_level') or 'INFO').upper()
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        return level if level in valid_levels else 'INFO'

    @property
    def enable_admin_panel(self) -> bool:
        """Enable admin statistics panel."""
        return self._get('enable_admin_panel', True) not in (False, 'false', '0')

    @property
    def rate_limit_enabled(self) -> bool:
        """Enable per-user rate limiting."""
        return self._get('rate_limit_enabled', True) not in (False, 'false', '0')

    @property
    def max_requests_per_minute(self) -> int:
        """Maximum requests per minute per user."""
        try:
            limit = int(self._get('max_requests_per_minute', 10))
            return max(1, min(limit, 60))  # Clamp between 1-60
        except (ValueError, TypeError):
            return 10

    @property
    def db_path(self) -> Path:
        """Database file path."""
        # Home Assistant: /share/su_urunleri_bot/
        # Local: current directory
        if Path('/share').exists():
            path = Path('/share/su_urunleri_bot/su_urunleri_kolluk.db')
        else:
            path = Path('./su_urunleri_kolluk.db')
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        """Data assets directory path."""
        if Path('/app/data').exists():
            return Path('/app/data')
        return Path(__file__).parent.parent / 'data'

    @property
    def logs_path(self) -> Path:
        """Logs directory path."""
        if Path('/share').exists():
            path = Path('/share/su_urunleri_bot/logs')
        else:
            path = Path('./logs')
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _parse_ids(value) -> Set[int]:
        """Parse various formats of user IDs into a set of integers."""
        if not value:
            return set()

        user_ids: Set[int] = set()
        raw = str(value).strip()

        if not raw:
            return user_ids

        # Try JSON array format first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, (int, str)):
                parsed = [parsed]
            if isinstance(parsed, list):
                for item in parsed:
                    try:
                        uid_str = str(item).split(':', 1)[0].strip()
                        user_ids.add(int(uid_str))
                    except (ValueError, IndexError):
                        pass
                return user_ids
        except (json.JSONDecodeError, TypeError):
            pass

        # Try comma/semicolon/newline separated format
        for part in re.split(r'[,;\n\s]+', raw.strip('[]')):
            part = part.strip().strip('"\'')
            if not part:
                continue
            try:
                uid_str = part.split(':', 1)[0].strip()
                user_ids.add(int(uid_str))
            except ValueError:
                pass

        return user_ids

    def to_dict(self) -> Dict:
        """Export configuration as dictionary (sensitive values excluded)."""
        return {
            'admin_ids': sorted(self.admin_ids),
            'allowed_user_ids': sorted(self.allowed_user_ids),
            'result_limit': self.result_limit,
            'timezone': str(self.timezone),
            'log_level': self.log_level,
            'enable_admin_panel': self.enable_admin_panel,
            'rate_limit_enabled': self.rate_limit_enabled,
            'max_requests_per_minute': self.max_requests_per_minute,
        }

    def __repr__(self) -> str:
        return f"<Config {self.to_dict()}>"


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global config (useful for testing)."""
    global _config
    _config = None
