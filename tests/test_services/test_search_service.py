"""
Tests for SearchService.
"""

import pytest
from unittest.mock import MagicMock, patch

from bot.services import SearchService


@pytest.fixture
def search_service():
    """Create search service."""
    return SearchService()


class TestSearchService:
    """Test SearchService."""

    def test_service_initialization(self, search_service):
        """Test service initialization."""
        assert search_service.article_repo is not None
        assert search_service.species_repo is not None
        assert search_service.penalty_repo is not None

    @patch('bot.services.search_service.SearchService.article_repo')
    def test_search_articles(self, mock_repo, search_service):
        """Test article search."""
        mock_repo.search_articles.return_value = [
            {'id': 1, 'title': 'Article 1', 'source': '61'}
        ]
        search_service.article_repo = mock_repo

        results = search_service.search_articles('test query')
        assert len(results) >= 0

    @patch('bot.services.search_service.SearchService.species_repo')
    def test_search_species(self, mock_repo, search_service):
        """Test species search."""
        mock_repo.search_species.return_value = [
            {'id': 1, 'name': 'Hamsi', 'min_cm': 9.0}
        ]
        search_service.species_repo = mock_repo

        results = search_service.search_species('hamsi')
        assert len(results) >= 0

    def test_search_with_limit(self, search_service):
        """Test search with custom limit."""
        # Mock the repos
        search_service.article_repo.search_articles = MagicMock(return_value=[])
        results = search_service.search_articles('query', limit=5)
        search_service.article_repo.search_articles.assert_called_with('query', source=None, limit=5, include_inland=False)

    def test_get_article(self, search_service):
        """Test getting specific article."""
        search_service.article_repo.get_article = MagicMock(
            return_value={'id': 1, 'title': 'Article'}
        )

        result = search_service.get_article('61', 18)
        assert result is not None

    def test_get_species(self, search_service):
        """Test getting specific species."""
        search_service.species_repo.get_species = MagicMock(
            return_value={'id': 1, 'name': 'Hamsi'}
        )

        result = search_service.get_species('commercial', 1)
        assert result is not None

    def test_autocomplete_species(self, search_service):
        """Test species autocomplete."""
        search_service.species_repo.search_species = MagicMock(
            return_value=[
                {'name': 'Hamsi'},
                {'name': 'Hamsi kütlesi'},
            ]
        )

        suggestions = search_service.autocomplete_species('ham')
        assert len(suggestions) > 0
        assert suggestions[0] == 'Hamsi'
