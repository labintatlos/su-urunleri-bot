"""
Search service for articles, species, penalties, and other searchable content.
"""

from typing import List, Dict, Optional

from bot.db import (
    get_article_repo,
    get_species_repo,
    get_penalty_repo,
)
from bot.exceptions import SearchError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class SearchService:
    """Service for searching articles, species, and penalties."""

    def __init__(self):
        """Initialize search service."""
        self.article_repo = get_article_repo()
        self.species_repo = get_species_repo()
        self.penalty_repo = get_penalty_repo()

    def search_articles(
        self,
        query: str,
        source: Optional[str] = None,
        limit: int = 8,
        include_inland: bool = False,
    ) -> List[Dict]:
        """Search articles by query."""
        try:
            results = self.article_repo.search_articles(
                query,
                source=source,
                limit=limit,
                include_inland=include_inland,
            )
            logger.info(
                "Article search",
                extra={
                    'query': query,
                    'source': source,
                    'results': len(results),
                }
            )
            return results
        except Exception as e:
            logger.error(f"Article search failed: {e}", extra={'query': query})
            raise SearchError(f"Article search failed: {e}") from e

    def search_species(
        self,
        query: str,
        kind: str = 'commercial',
        limit: int = 10,
    ) -> List[Dict]:
        """Search species by name."""
        try:
            results = self.species_repo.search_species(
                query,
                kind=kind,
                limit=limit,
            )
            logger.info(
                "Species search",
                extra={
                    'query': query,
                    'kind': kind,
                    'results': len(results),
                }
            )
            return results
        except Exception as e:
            logger.error(f"Species search failed: {e}", extra={'query': query})
            raise SearchError(f"Species search failed: {e}") from e

    def search_prohibited_species(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict]:
        """Search prohibited species."""
        try:
            results = self.species_repo.search_prohibited(query, limit=limit)
            logger.info(
                "Prohibited species search",
                extra={
                    'query': query,
                    'results': len(results),
                }
            )
            return results
        except Exception as e:
            logger.error(f"Prohibited species search failed: {e}", extra={'query': query})
            raise SearchError(f"Prohibited species search failed: {e}") from e

    def search_penalties(
        self,
        query: str,
        limit: int = 8,
    ) -> List[Dict]:
        """Search penalty cards."""
        try:
            results = self.penalty_repo.search_penalties(query, limit=limit)
            logger.info(
                "Penalty search",
                extra={
                    'query': query,
                    'results': len(results),
                }
            )
            return results
        except Exception as e:
            logger.error(f"Penalty search failed: {e}", extra={'query': query})
            raise SearchError(f"Penalty search failed: {e}") from e

    def get_article(
        self,
        source: str,
        article: int,
    ) -> Optional[Dict]:
        """Get specific article."""
        try:
            result = self.article_repo.get_article(source, article)
            if result:
                logger.debug(
                    "Article retrieved",
                    extra={'source': source, 'article': article}
                )
            return result
        except Exception as e:
            logger.error(
                f"Failed to get article: {e}",
                extra={'source': source, 'article': article}
            )
            raise SearchError(f"Failed to get article: {e}") from e

    def get_species(
        self,
        kind: str,
        species_id: int,
    ) -> Optional[Dict]:
        """Get specific species."""
        try:
            result = self.species_repo.get_species(kind, species_id)
            if result:
                logger.debug(
                    "Species retrieved",
                    extra={'kind': kind, 'species_id': species_id}
                )
            return result
        except Exception as e:
            logger.error(
                f"Failed to get species: {e}",
                extra={'kind': kind, 'species_id': species_id}
            )
            raise SearchError(f"Failed to get species: {e}") from e

    def get_penalty(
        self,
        penalty_id: int,
    ) -> Optional[Dict]:
        """Get specific penalty card."""
        try:
            result = self.penalty_repo.get_penalty(penalty_id)
            if result:
                logger.debug("Penalty retrieved", extra={'penalty_id': penalty_id})
            return result
        except Exception as e:
            logger.error(f"Failed to get penalty: {e}", extra={'penalty_id': penalty_id})
            raise SearchError(f"Failed to get penalty: {e}") from e

    def list_articles(
        self,
        source: str,
        include_inland: bool = False,
    ) -> List[Dict]:
        """List all articles for a source."""
        try:
            results = self.article_repo.list_articles(
                source,
                include_inland=include_inland,
            )
            logger.info(
                "Articles listed",
                extra={
                    'source': source,
                    'count': len(results),
                }
            )
            return results
        except Exception as e:
            logger.error(f"Failed to list articles: {e}", extra={'source': source})
            raise SearchError(f"Failed to list articles: {e}") from e

    def autocomplete_species(
        self,
        query: str,
        kind: str = 'commercial',
        limit: int = 5,
    ) -> List[str]:
        """Get autocomplete suggestions for species."""
        try:
            results = self.species_repo.search_species(
                query,
                kind=kind,
                limit=limit,
            )
            suggestions = [r['name'] for r in results]
            logger.debug(
                "Species autocomplete",
                extra={
                    'query': query,
                    'suggestions': len(suggestions),
                }
            )
            return suggestions
        except Exception as e:
            logger.warning(f"Autocomplete failed: {e}")
            return []
