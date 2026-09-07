"""
Penalty service for fine calculations and penalty card lookups.
"""

from typing import Dict, Optional, List

from bot.db import get_penalty_repo
from bot.exceptions import ServiceError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class PenaltyService:
    """Service for penalty calculations and lookups."""

    def __init__(self):
        """Initialize penalty service."""
        self.repo = get_penalty_repo()

    def get_penalty(self, penalty_id: int) -> Optional[Dict]:
        """Get penalty card by ID."""
        try:
            return self.repo.get_penalty(penalty_id)
        except Exception as e:
            logger.error(f"Failed to get penalty: {e}")
            raise ServiceError(f"Failed to get penalty: {e}") from e

    def search_penalties(self, query: str, limit: int = 8) -> List[Dict]:
        """Search penalty cards."""
        try:
            return self.repo.search_penalties(query, limit=limit)
        except Exception as e:
            logger.error(f"Penalty search failed: {e}")
            raise ServiceError(f"Penalty search failed: {e}") from e

    def calculate_penalty(
        self,
        penalty: Dict,
        violation_type: str = 'first',
        is_repeat: bool = False,
    ) -> float:
        """Calculate penalty amount."""
        amounts = penalty.get('amounts', {})

        if is_repeat and 'repeat' in amounts:
            return float(amounts.get('repeat', 0))

        return float(amounts.get(violation_type, amounts.get('first', 0)))

    def get_violation_details(self, penalty: Dict) -> Dict:
        """Get violation details from penalty card."""
        return {
            'violation': penalty.get('violation', ''),
            'option': penalty.get('option_text', ''),
            'law': penalty.get('law', ''),
            'regulation': penalty.get('regulation', ''),
            'teblig': penalty.get('teblig', ''),
            'base_amount': penalty.get('base_ipc', 0),
            'product_seizure': penalty.get('product_seizure', ''),
            'means_seizure': penalty.get('means_seizure', ''),
            'license_action': penalty.get('license_action', ''),
        }

    def check_product_seizure(self, penalty: Dict) -> bool:
        """Check if product seizure applies."""
        seizure = penalty.get('product_seizure', '')
        return seizure.lower() in ('evet', 'yes', '1', 'true')

    def check_means_seizure(self, penalty: Dict) -> bool:
        """Check if fishing equipment seizure applies."""
        seizure = penalty.get('means_seizure', '')
        return seizure.lower() in ('evet', 'yes', '1', 'true')

    def get_repeat_multiplier(self, penalty: Dict) -> float:
        """Get repeat violation multiplier."""
        text = penalty.get('repeat_text', '')
        if 'iki' in text.lower() and 'kat' in text.lower():
            return 2.0
        elif 'üç' in text.lower() and 'kat' in text.lower():
            return 3.0
        return 1.0

    def format_penalty_info(self, penalty: Dict) -> str:
        """Format penalty information as readable text."""
        lines = [
            f"<b>{penalty.get('violation', 'İhlal')}</b>",
            f"Seçenek: {penalty.get('option_text', '')}",
            f"Dayanak: {penalty.get('law', '')}",
        ]

        if penalty.get('regulation'):
            lines.append(f"Yönetmelik: {penalty.get('regulation')}")

        base = penalty.get('base_ipc', 0)
        if base:
            lines.append(f"Taban Ceza: {base:,.0f} TL")

        if penalty.get('product_seizure'):
            lines.append("✓ Ürün el konuşu")

        if penalty.get('means_seizure'):
            lines.append("✓ Av aracına el konuşu")

        if penalty.get('repeat_text'):
            lines.append(f"Tekrar: {penalty.get('repeat_text')}")

        return "\n".join(lines)

    def search_by_violation(self, violation_term: str) -> List[Dict]:
        """Search penalties by violation term."""
        try:
            return self.search_penalties(violation_term)
        except Exception as e:
            logger.error(f"Violation search failed: {e}")
            return []
