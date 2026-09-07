"""
Species service for fish species identification and validation.
"""

from datetime import datetime
from typing import List, Dict, Optional

from bot.db import get_species_repo
from bot.exceptions import ServiceError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class SpeciesService:
    """Service for species operations."""

    def __init__(self):
        """Initialize species service."""
        self.repo = get_species_repo()

    def get_species(self, kind: str, species_id: int) -> Optional[Dict]:
        """Get species by ID."""
        try:
            return self.repo.get_species(kind, species_id)
        except Exception as e:
            logger.error(f"Failed to get species: {e}")
            raise ServiceError(f"Failed to get species: {e}") from e

    def search_species(self, query: str, kind: str = 'commercial') -> List[Dict]:
        """Search species by name."""
        try:
            return self.repo.search_species(query, kind=kind)
        except Exception as e:
            logger.error(f"Species search failed: {e}")
            raise ServiceError(f"Species search failed: {e}") from e

    def check_size_compliance(
        self,
        species: Dict,
        size_cm: float,
    ) -> Dict:
        """Check if species size complies with regulations."""
        min_size = species.get('min_cm')
        is_compliant = min_size is None or size_cm >= min_size

        return {
            'compliant': is_compliant,
            'size_cm': size_cm,
            'min_size_cm': min_size,
            'violation': None if is_compliant else f"Boy limiti: {min_size} cm",
        }

    def check_season_compliance(
        self,
        species: Dict,
        check_date: datetime = None,
    ) -> Dict:
        """Check if species is in allowed season."""
        if check_date is None:
            check_date = datetime.now()

        time_bans = species.get('time_bans', [])
        if not time_bans:
            return {
                'compliant': True,
                'banned': False,
                'ban_periods': [],
            }

        is_banned = self._is_in_ban_period(check_date, time_bans)

        return {
            'compliant': not is_banned,
            'banned': is_banned,
            'ban_periods': time_bans,
            'violation': 'Mevsimde yasak' if is_banned else None,
        }

    def check_catch_limit(
        self,
        species: Dict,
        catch_amount: float,
        kind: str = 'amateur',
    ) -> Dict:
        """Check if catch amount complies with limits."""
        if kind == 'amateur':
            limit_text = species.get('limit_text', 'Limit yok')
            return {
                'compliant': True,
                'limit': limit_text,
                'amount': catch_amount,
            }

        return {
            'compliant': True,
            'limit': 'Ticari',
            'amount': catch_amount,
        }

    @staticmethod
    def _is_in_ban_period(check_date: datetime, ban_periods: List[str]) -> bool:
        """Check if date is in any ban period."""
        month = check_date.month
        day = check_date.day
        current = (month, day)

        for period in ban_periods:
            parts = period.split('/')
            if len(parts) != 2:
                continue

            try:
                start_parts = parts[0].split('-')
                end_parts = parts[1].split('-')

                start_month, start_day = int(start_parts[0]), int(start_parts[1])
                end_month, end_day = int(end_parts[0]), int(end_parts[1])

                start = (start_month, start_day)
                end = (end_month, end_day)

                if start <= end:
                    if start <= current <= end:
                        return True
                else:
                    if current >= start or current <= end:
                        return True
            except (ValueError, IndexError):
                continue

        return False

    def get_commercial_species(self, species_id: int) -> Optional[Dict]:
        """Get commercial species by ID."""
        return self.get_species('commercial', species_id)

    def get_amateur_species(self, species_id: int) -> Optional[Dict]:
        """Get amateur species by ID."""
        return self.get_species('amateur', species_id)

    def search_commercial(self, query: str) -> List[Dict]:
        """Search commercial species."""
        return self.search_species(query, kind='commercial')

    def search_amateur(self, query: str) -> List[Dict]:
        """Search amateur species."""
        return self.search_species(query, kind='amateur')

    def validate_species(
        self,
        species: Dict,
        size_cm: Optional[float] = None,
        kind: str = 'commercial',
    ) -> Dict:
        """Validate species compliance."""
        validations = {
            'species_name': species.get('name'),
            'size_check': None,
            'season_check': None,
            'limit_check': None,
            'violations': [],
        }

        if size_cm is not None:
            size_check = self.check_size_compliance(species, size_cm)
            validations['size_check'] = size_check
            if not size_check['compliant']:
                validations['violations'].append(size_check['violation'])

        season_check = self.check_season_compliance(species)
        validations['season_check'] = season_check
        if not season_check['compliant']:
            validations['violations'].append(season_check['violation'])

        validations['is_valid'] = len(validations['violations']) == 0

        return validations
