"""
Admin service for statistics, user management, and analytics.
"""

from typing import Dict, List

from bot.db import get_admin_repo, get_user_repo, get_query_log_repo
from bot.exceptions import ServiceError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class AdminService:
    """Service for admin operations."""

    def __init__(self):
        """Initialize admin service."""
        self.admin_repo = get_admin_repo()
        self.user_repo = get_user_repo()
        self.log_repo = get_query_log_repo()

    def get_stats(self) -> Dict:
        """Get overall statistics."""
        try:
            stats = self.admin_repo.get_stats()
            logger.debug("Stats retrieved")
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise ServiceError(f"Failed to get stats: {e}") from e

    def get_user_activity(self) -> List[Dict]:
        """Get user activity statistics."""
        try:
            activity = self.admin_repo.get_user_activity()
            logger.debug(f"User activity retrieved: {len(activity)} users")
            return activity
        except Exception as e:
            logger.error(f"Failed to get user activity: {e}")
            raise ServiceError(f"Failed to get user activity: {e}") from e

    def get_audit_stats(self) -> Dict:
        """Get audit-related statistics."""
        try:
            stats = self.admin_repo.get_audit_stats()
            logger.debug("Audit stats retrieved")
            return stats
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            raise ServiceError(f"Failed to get audit stats: {e}") from e

    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent query logs."""
        try:
            logs = self.log_repo.get_recent_logs(limit=limit)
            logger.debug(f"Recent logs retrieved: {len(logs)} entries")
            return logs
        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            raise ServiceError(f"Failed to get recent logs: {e}") from e

    def get_user_stats(self, user_id: int) -> Dict:
        """Get stats for specific user."""
        try:
            user = self.user_repo.get_user(user_id)
            history = self.log_repo.get_user_history(user_id)

            return {
                'user': user,
                'query_count': len(history),
                'recent_queries': history[:10],
            }
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            raise ServiceError(f"Failed to get user stats: {e}") from e

    def list_users(self, limit: int = 100) -> List[Dict]:
        """List all users."""
        try:
            users = self.user_repo.list_users(limit=limit)
            logger.debug(f"Users listed: {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise ServiceError(f"Failed to list users: {e}") from e

    def get_action_stats(self, action: str = None) -> List[Dict]:
        """Get action statistics."""
        try:
            stats = self.log_repo.get_action_stats(action=action)
            logger.debug(f"Action stats retrieved: {len(stats)} actions")
            return stats
        except Exception as e:
            logger.error(f"Failed to get action stats: {e}")
            raise ServiceError(f"Failed to get action stats: {e}") from e

    def format_stats_report(self) -> str:
        """Format statistics as readable report."""
        try:
            stats = self.get_stats()
            audit_stats = self.get_audit_stats()

            lines = [
                "<b>📊 BOT İSTATİSTİKLERİ</b>",
                "",
                f"👥 Toplam Kullanıcı: {stats.get('total_users', 0)}",
                f"🔍 Toplam Sorgu: {stats.get('total_queries', 0)}",
                "",
            ]

            if audit_stats.get('searches'):
                lines.append("<b>🔝 En Çok Aranan:</b>")
                for item in audit_stats['searches'][:5]:
                    lines.append(f"  • {item.get('query', '')}: {item.get('count', 0)}")
                lines.append("")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to format stats report: {e}")
            return "İstatistik raporlaması başarısız."
