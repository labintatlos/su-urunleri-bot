"""
Database module with connection management and repository pattern.
"""

from bot.db.connection import (
    DatabaseConnection,
    get_db,
    reset_db,
)

from bot.db.repository import (
    Repository,
    UserRepository,
    QueryLogRepository,
    ArticleRepository,
    SpeciesRepository,
    PenaltyRepository,
    FavoriteRepository,
    AdminRepository,
    get_user_repo,
    get_query_log_repo,
    get_article_repo,
    get_species_repo,
    get_penalty_repo,
    get_favorite_repo,
    get_admin_repo,
)

from bot.db.migrations.runner import (
    MigrationRunner,
    get_migration_runner,
)

__all__ = [
    "DatabaseConnection",
    "get_db",
    "reset_db",
    "Repository",
    "UserRepository",
    "QueryLogRepository",
    "ArticleRepository",
    "SpeciesRepository",
    "PenaltyRepository",
    "FavoriteRepository",
    "AdminRepository",
    "get_user_repo",
    "get_query_log_repo",
    "get_article_repo",
    "get_species_repo",
    "get_penalty_repo",
    "get_favorite_repo",
    "get_admin_repo",
    "MigrationRunner",
    "get_migration_runner",
]
