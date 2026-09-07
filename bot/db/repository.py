"""
Data access layer (Repository pattern) for all database operations.
Provides a clean interface for CRUD operations across all entities.
"""

import json
import re
import unicodedata
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple

from bot.db.connection import get_db
from bot.exceptions import DatabaseError, NotFoundError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class Repository:
    """Base repository with common database operations."""

    def __init__(self):
        """Initialize repository."""
        self.db = get_db()

    @staticmethod
    def normalize(value: str) -> str:
        """Normalize text for search (Turkish-friendly)."""
        s = str(value or '').lower()
        # Turkish character mapping
        s = s.translate(str.maketrans({
            'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
        }))
        # Remove diacritics
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(ch for ch in s if not unicodedata.combining(ch))
        # Tokenize
        s = re.sub(r'[^a-z0-9]+', ' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    @staticmethod
    def escape(value: str) -> str:
        """HTML escape a value."""
        import html
        return html.escape(str(value or ''))

    def execute(self, query: str, params: Tuple = ()) -> Any:
        """Execute a query."""
        try:
            cursor = self.db.execute(query, params)
            self.db.commit()
            return cursor
        except Exception as e:
            logger.error(f"Query failed: {query}", extra={'error': str(e)})
            raise DatabaseError(f"Query execution failed: {e}") from e

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict]:
        """Fetch a single row as dictionary."""
        try:
            cursor = self.db.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            raise DatabaseError(f"Fetch one failed: {e}") from e

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict]:
        """Fetch all rows as list of dictionaries."""
        try:
            cursor = self.db.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Fetch all failed: {e}") from e


class UserRepository(Repository):
    """Repository for user-related operations."""

    def touch_user(self, user_id: int, username: Optional[str] = None,
                   first_name: Optional[str] = None, custom_name: Optional[str] = None) -> None:
        """Record or update a user (upsert)."""
        name = custom_name or first_name or ''
        query = '''
            INSERT INTO users(user_id, username, first_name, last_seen)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_seen=excluded.last_seen
        '''
        self.execute(query, (user_id, username, name, datetime.now().isoformat()))
        logger.info("User recorded", extra={'user_id': user_id, 'username': username})

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        return self.fetch_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )

    def list_users(self, limit: int = 100) -> List[Dict]:
        """List all users."""
        return self.fetch_all(
            'SELECT * FROM users ORDER BY last_seen DESC LIMIT ?',
            (limit,)
        )

    def count_users(self) -> int:
        """Get total user count."""
        row = self.fetch_one('SELECT COUNT(*) as count FROM users')
        return row['count'] if row else 0


class QueryLogRepository(Repository):
    """Repository for query logging."""

    def log_query(self, user_id: int, action: str, query: str = '') -> None:
        """Log a user query."""
        self.execute(
            '''INSERT INTO query_log(user_id, action, query, created_at)
               VALUES(?, ?, ?, ?)''',
            (user_id, action, query, datetime.now().isoformat())
        )

    def get_user_history(self, user_id: int, limit: int = 30) -> List[Dict]:
        """Get user's query history."""
        return self.fetch_all(
            '''SELECT * FROM query_log
               WHERE user_id = ?
               ORDER BY id DESC
               LIMIT ?''',
            (user_id, limit)
        )

    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent query logs across all users."""
        return self.fetch_all(
            '''SELECT q.*, u.username, u.first_name
               FROM query_log q
               LEFT JOIN users u ON u.user_id = q.user_id
               ORDER BY q.id DESC
               LIMIT ?''',
            (limit,)
        )

    def get_action_stats(self, action: str = None) -> List[Dict]:
        """Get action statistics."""
        if action:
            query = '''SELECT action, COUNT(*) as count
                       FROM query_log
                       WHERE action LIKE ?
                       GROUP BY action
                       ORDER BY count DESC'''
            return self.fetch_all(query, (f'{action}%',))
        else:
            query = '''SELECT action, COUNT(*) as count
                       FROM query_log
                       GROUP BY action
                       ORDER BY count DESC'''
            return self.fetch_all(query)


class ArticleRepository(Repository):
    """Repository for article/regulation searches."""

    def get_article(self, source: str, article: int) -> Optional[Dict]:
        """Get specific article."""
        return self.fetch_one(
            'SELECT * FROM articles WHERE source = ? AND article = ?',
            (source, article)
        )

    def list_articles(self, source: str, include_inland: bool = False) -> List[Dict]:
        """List all articles for a source."""
        if include_inland:
            query = 'SELECT * FROM articles WHERE source = ? ORDER BY article'
            params = (source,)
        else:
            query = "SELECT * FROM articles WHERE source = ? AND scope != 'inland' ORDER BY article"
            params = (source,)
        return self.fetch_all(query, params)

    def search_articles(self, query: str, source: str = None, limit: int = 8,
                       include_inland: bool = False) -> List[Dict]:
        """Search articles by query."""
        search_query = self.normalize(query)

        conditions = []
        params = []

        if source:
            conditions.append('source = ?')
            params.append(source)

        if not include_inland:
            conditions.append("scope != 'inland'")

        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        sql = f'''SELECT * FROM articles WHERE {where_clause} ORDER BY article LIMIT ?'''
        params.append(limit)

        rows = self.fetch_all(sql, tuple(params))

        # Score results by relevance
        scored = []
        for row in rows:
            score = self._score_match(search_query, row.get('search_text', ''), row.get('title', ''))
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: -x[0])
        return [row for _, row in scored[:limit]]

    @staticmethod
    def _score_match(query: str, text: str, title: str) -> int:
        """Score a search result."""
        terms = query.split()
        score = 0

        text_tokens = set(text.split())
        title_tokens = set(title.split())

        for term in terms:
            if term in text_tokens:
                score += 10
            elif any(tok.startswith(term) for tok in text_tokens):
                score += 5

            if term in title_tokens:
                score += 20
            elif any(tok.startswith(term) for tok in title_tokens):
                score += 10

        return score if len(terms) <= 2 else score if score > len(terms) * 5 else 0


class SpeciesRepository(Repository):
    """Repository for species data."""

    def get_species(self, kind: str, species_id: int) -> Optional[Dict]:
        """Get species by ID."""
        table = 'commercial_species' if kind == 'commercial' else 'amateur_species'
        row = self.fetch_one(
            f'SELECT * FROM {table} WHERE id = ?',
            (species_id,)
        )
        if row:
            row['time_bans'] = json.loads(row.get('time_bans', '[]'))
        return row

    def search_species(self, query: str, kind: str = 'commercial', limit: int = 10) -> List[Dict]:
        """Search species by name."""
        table = 'commercial_species' if kind == 'commercial' else 'amateur_species'
        search_query = self.normalize(query)

        rows = self.fetch_all(
            f'SELECT * FROM {table} ORDER BY name',
        )

        # Score results
        scored = []
        for row in rows:
            score = self._score_match(search_query, row.get('search_text', ''), row.get('name', ''))
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: -x[0])

        result = []
        for _, row in scored[:limit]:
            row['time_bans'] = json.loads(row.get('time_bans', '[]'))
            result.append(row)
        return result

    def search_prohibited(self, query: str, limit: int = 10) -> List[Dict]:
        """Search prohibited species."""
        search_query = self.normalize(query)
        rows = self.fetch_all('SELECT * FROM prohibited_species ORDER BY name')

        scored = []
        for row in rows:
            score = self._score_match(search_query, row.get('search_text', ''), row.get('name', ''))
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: -x[0])
        return [row for _, row in scored[:limit]]

    @staticmethod
    def _score_match(query: str, text: str, name: str) -> int:
        """Score a species match."""
        terms = query.split()
        score = 0
        text_tokens = set(text.split())
        name_tokens = set(name.split())

        for term in terms:
            if term in text_tokens:
                score += 5
            if term in name_tokens:
                score += 20
        return score


class PenaltyRepository(Repository):
    """Repository for penalty cards."""

    def get_penalty(self, penalty_id: int) -> Optional[Dict]:
        """Get penalty card by ID."""
        row = self.fetch_one(
            'SELECT * FROM penalty_cards WHERE id = ?',
            (penalty_id,)
        )
        if row:
            row['amounts'] = json.loads(row.get('amounts', '{}'))
        return row

    def search_penalties(self, query: str, limit: int = 8) -> List[Dict]:
        """Search penalty cards."""
        search_query = self.normalize(query)
        rows = self.fetch_all(
            "SELECT * FROM penalty_cards WHERE scope != 'inland' ORDER BY source_row"
        )

        scored = []
        for row in rows:
            score = self._score_match(
                search_query,
                row.get('search_text', ''),
                row.get('violation', ''),
                row.get('option_text', '')
            )
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: (-x[0], x[1].get('source_row', 0)))

        result = []
        for _, row in scored[:limit]:
            row['amounts'] = json.loads(row.get('amounts', '{}'))
            result.append(row)
        return result

    @staticmethod
    def _score_match(query: str, search_text: str, violation: str, option: str) -> int:
        """Score a penalty match."""
        terms = query.split()
        score = 0

        all_text = f"{search_text} {violation} {option}"
        tokens = set(all_text.split())

        for term in terms:
            if term in tokens:
                score += 10
            elif any(tok.startswith(term) for tok in tokens):
                score += 5

        if f' {query} ' in f' {search_text} ':
            score += 30

        return score


class FavoriteRepository(Repository):
    """Repository for user favorites."""

    def add_favorite(self, user_id: int, item_type: str, item_id: str) -> None:
        """Add item to favorites."""
        self.execute(
            '''INSERT OR IGNORE INTO favorites(user_id, item_type, item_id, created_at)
               VALUES(?, ?, ?, ?)''',
            (user_id, item_type, str(item_id), datetime.now().isoformat())
        )
        logger.info(
            "Favorite added",
            extra={'user_id': user_id, 'item_type': item_type, 'item_id': item_id}
        )

    def get_favorites(self, user_id: int, limit: int = 30) -> List[Dict]:
        """Get user's favorites."""
        return self.fetch_all(
            '''SELECT * FROM favorites
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?''',
            (user_id, limit)
        )

    def remove_favorite(self, user_id: int, item_type: str, item_id: str) -> None:
        """Remove item from favorites."""
        self.execute(
            'DELETE FROM favorites WHERE user_id = ? AND item_type = ? AND item_id = ?',
            (user_id, item_type, str(item_id))
        )


class AdminRepository(Repository):
    """Repository for admin statistics."""

    def get_stats(self) -> Dict:
        """Get overall statistics."""
        users = self.fetch_one('SELECT COUNT(*) as count FROM users')
        total_queries = self.fetch_one('SELECT COUNT(*) as count FROM query_log')

        return {
            'total_users': users['count'] if users else 0,
            'total_queries': total_queries['count'] if total_queries else 0,
        }

    def get_user_activity(self) -> List[Dict]:
        """Get user activity statistics."""
        return self.fetch_all(
            '''SELECT u.user_id, u.username, u.first_name, u.last_seen, COUNT(q.id) as query_count
               FROM users u
               LEFT JOIN query_log q ON q.user_id = u.user_id
               GROUP BY u.user_id
               ORDER BY query_count DESC'''
        )

    def get_audit_stats(self) -> Dict:
        """Get audit-related statistics."""
        result = {}

        # Guide usage
        guides = self.fetch_all(
            '''SELECT query, COUNT(*) as count
               FROM query_log
               WHERE action LIKE 'guide:%' OR action LIKE 'audit:%'
               GROUP BY query
               ORDER BY count DESC
               LIMIT 15'''
        )
        result['guides'] = guides

        # Search terms
        searches = self.fetch_all(
            '''SELECT query, COUNT(*) as count
               FROM query_log
               WHERE query != '' AND query IS NOT NULL AND action LIKE '%search%'
               GROUP BY query
               ORDER BY count DESC
               LIMIT 10'''
        )
        result['searches'] = searches

        return result


# Convenience functions to get repositories

def get_user_repo() -> UserRepository:
    """Get user repository."""
    return UserRepository()


def get_query_log_repo() -> QueryLogRepository:
    """Get query log repository."""
    return QueryLogRepository()


def get_article_repo() -> ArticleRepository:
    """Get article repository."""
    return ArticleRepository()


def get_species_repo() -> SpeciesRepository:
    """Get species repository."""
    return SpeciesRepository()


def get_penalty_repo() -> PenaltyRepository:
    """Get penalty repository."""
    return PenaltyRepository()


def get_favorite_repo() -> FavoriteRepository:
    """Get favorite repository."""
    return FavoriteRepository()


def get_admin_repo() -> AdminRepository:
    """Get admin repository."""
    return AdminRepository()
