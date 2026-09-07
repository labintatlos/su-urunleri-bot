"""
Database migration runner.
Handles schema versioning, initialization, and upgrades.
"""

import json
from pathlib import Path
from typing import List, Dict

from bot.db.connection import get_db
from bot.exceptions import MigrationError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class MigrationRunner:
    """Manages database migrations and schema versioning."""

    DATASET_VERSION = 'v4'

    def __init__(self):
        """Initialize migration runner."""
        self.db = get_db()
        self.migrations_dir = Path(__file__).parent

    def init_db(self, data_dir: Path) -> None:
        """Initialize database with schema and data."""
        try:
            # Create schema
            self._create_schema()

            # Check dataset version
            self._check_and_update_dataset(data_dir)

            # Create indexes
            self._create_indexes()

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise MigrationError(f"Database init failed: {e}") from e

    def _create_schema(self) -> None:
        """Create base database schema."""
        schema_sql = '''
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS meta(
            k TEXT PRIMARY KEY,
            v TEXT
        );

        CREATE TABLE IF NOT EXISTS sources(
            key TEXT PRIMARY KEY,
            title TEXT,
            type TEXT,
            number TEXT,
            filename TEXT,
            sha256 TEXT
        );

        CREATE TABLE IF NOT EXISTS articles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            article INTEGER,
            title TEXT,
            body TEXT,
            page_start INTEGER,
            page_end INTEGER,
            scope TEXT,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS rules(
            id TEXT PRIMARY KEY,
            cat TEXT,
            title TEXT,
            summary TEXT,
            refs TEXT,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS commercial_species(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            min_cm REAL,
            min_kg REAL,
            time_bans TEXT,
            article_time INTEGER,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS amateur_species(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            min_cm REAL,
            min_kg REAL,
            limit_text TEXT,
            time_bans TEXT,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS prohibited_species(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS penalty_cards(
            id INTEGER PRIMARY KEY,
            source_row INTEGER,
            violation TEXT,
            option_text TEXT,
            law TEXT,
            regulation TEXT,
            teblig TEXT,
            art36 TEXT,
            base_ipc REAL,
            amounts TEXT,
            product_seizure TEXT,
            means_seizure TEXT,
            repeat_text TEXT,
            license_action TEXT,
            notes TEXT,
            scope TEXT,
            layout TEXT,
            teblig_source TEXT,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS raw_excel_rows(
            source_row INTEGER PRIMARY KEY,
            raw_text TEXT,
            search_text TEXT
        );

        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_seen TEXT
        );

        CREATE TABLE IF NOT EXISTS query_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            query TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS favorites(
            user_id INTEGER,
            item_type TEXT,
            item_id TEXT,
            created_at TEXT,
            PRIMARY KEY(user_id, item_type, item_id)
        );

        CREATE TABLE IF NOT EXISTS audit_records(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            region TEXT,
            activity TEXT,
            vessel_length REAL,
            vessel_band TEXT,
            audit_date DATE,
            subject_category TEXT,
            fishing_gear TEXT,
            species TEXT,
            violations TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        '''

        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        logger.info("Schema created")

    def _create_indexes(self) -> None:
        """Create database indexes for performance."""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_articles_search ON articles(search_text)',
            'CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)',
            'CREATE INDEX IF NOT EXISTS idx_rules_search ON rules(search_text)',
            'CREATE INDEX IF NOT EXISTS idx_rules_cat ON rules(cat)',
            'CREATE INDEX IF NOT EXISTS idx_species_search ON commercial_species(search_text)',
            'CREATE INDEX IF NOT EXISTS idx_amateur_species_search ON amateur_species(search_text)',
            'CREATE INDEX IF NOT EXISTS idx_prohibited_search ON prohibited_species(search_text)',
            'CREATE INDEX IF NOT EXISTS idx_penalties_search ON penalty_cards(search_text)',
            'CREATE INDEX IF NOT EXISTS idx_penalties_layout ON penalty_cards(layout)',
            'CREATE INDEX IF NOT EXISTS idx_query_log_user ON query_log(user_id, created_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_query_log_action ON query_log(action)',
            'CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_records(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_records(created_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_users_created ON users(last_seen DESC)',
        ]

        conn = self.db._get_connection()
        cursor = conn.cursor()

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

        conn.commit()
        logger.info("Indexes created")

    def _check_and_update_dataset(self, data_dir: Path) -> None:
        """Check dataset version and load data if needed."""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        # Check current version
        cursor.execute("SELECT v FROM meta WHERE k='dataset'")
        row = cursor.fetchone()
        current_version = row[0] if row else None

        if current_version != self.DATASET_VERSION:
            logger.info(f"Upgrading dataset: {current_version} -> {self.DATASET_VERSION}")

            # Clear old data
            for table in ['sources', 'articles', 'rules', 'commercial_species',
                          'amateur_species', 'prohibited_species', 'penalty_cards', 'raw_excel_rows']:
                cursor.execute(f'DELETE FROM {table}')

            # Update version
            cursor.execute(
                "INSERT OR REPLACE INTO meta(k,v) VALUES('dataset',?)",
                (self.DATASET_VERSION,)
            )

            # Load data files
            try:
                self._load_data_files(data_dir, cursor)
            except Exception as e:
                logger.warning(f"Some data files could not be loaded: {e}")

            conn.commit()
            logger.info("Dataset updated successfully")

    def _load_data_files(self, data_dir: Path, cursor) -> None:
        """Load data from JSON files."""
        # Sources
        if (data_dir / 'sources.json').exists():
            with open(data_dir / 'sources.json', 'r', encoding='utf-8') as f:
                for src in json.load(f):
                    cursor.execute(
                        'INSERT INTO sources VALUES(?,?,?,?,?,?)',
                        (src['key'], src['title'], src['type'],
                         src.get('number', ''), src['filename'], src['sha256'])
                    )

        # Articles
        if (data_dir / 'articles.json').exists():
            with open(data_dir / 'articles.json', 'r', encoding='utf-8') as f:
                for a in json.load(f):
                    cursor.execute(
                        '''INSERT INTO articles(source,article,title,body,page_start,page_end,scope,search_text)
                           VALUES(?,?,?,?,?,?,?,?)''',
                        (a['source'], a['article'], a['title'], a['body'],
                         a['page_start'], a['page_end'], a['scope'],
                         a.get('search_text', ''))
                    )

        # Rules
        if (data_dir / 'field_rules.json').exists():
            with open(data_dir / 'field_rules.json', 'r', encoding='utf-8') as f:
                for r in json.load(f):
                    cursor.execute(
                        'INSERT INTO rules VALUES(?,?,?,?,?,?)',
                        (r['id'], r['cat'], r['title'], r['summary'],
                         json.dumps(r['refs'], ensure_ascii=False), r.get('search_text', ''))
                    )

        # Species
        if (data_dir / 'commercial_species.json').exists():
            with open(data_dir / 'commercial_species.json', 'r', encoding='utf-8') as f:
                for sp in json.load(f):
                    cursor.execute(
                        '''INSERT INTO commercial_species(name,min_cm,min_kg,time_bans,article_time,search_text)
                           VALUES(?,?,?,?,?,?)''',
                        (sp['name'], sp['min_cm'], sp['min_kg'],
                         json.dumps(sp['time_bans']), sp.get('article_time'), sp.get('search_text', ''))
                    )

        if (data_dir / 'amateur_species.json').exists():
            with open(data_dir / 'amateur_species.json', 'r', encoding='utf-8') as f:
                for sp in json.load(f):
                    cursor.execute(
                        '''INSERT INTO amateur_species(name,min_cm,min_kg,limit_text,time_bans,search_text)
                           VALUES(?,?,?,?,?,?)''',
                        (sp['name'], sp['min_cm'], sp['min_kg'],
                         sp.get('limit', ''), json.dumps(sp['time_bans']), sp.get('search_text', ''))
                    )

        # Prohibited species
        if (data_dir / 'prohibited_species.json').exists():
            with open(data_dir / 'prohibited_species.json', 'r', encoding='utf-8') as f:
                for sp in json.load(f):
                    cursor.execute(
                        'INSERT INTO prohibited_species(name,search_text) VALUES(?,?)',
                        (sp['name'], sp.get('search_text', ''))
                    )

        # Penalty cards
        if (data_dir / 'penalty_cards.json').exists():
            with open(data_dir / 'penalty_cards.json', 'r', encoding='utf-8') as f:
                for pc in json.load(f):
                    search = pc.get('search_text', '')
                    cursor.execute(
                        '''INSERT INTO penalty_cards
                           (id,source_row,violation,option_text,law,regulation,teblig,art36,
                            base_ipc,amounts,product_seizure,means_seizure,repeat_text,
                            license_action,notes,scope,layout,teblig_source,search_text)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (pc['id'], pc['source_row'], pc['violation'], pc.get('option'),
                         pc.get('law'), pc.get('regulation'), pc.get('teblig'), pc.get('art36'),
                         pc.get('base_ipc'), json.dumps(pc.get('amounts') or {}, ensure_ascii=False),
                         pc.get('product_seizure'), pc.get('means_seizure'), pc.get('repeat'),
                         pc.get('license_action'), pc.get('notes'), pc.get('scope', 'sea_or_general'),
                         pc.get('layout'), pc.get('teblig_source'), search)
                    )

        # Raw Excel rows
        if (data_dir / 'raw_excel_rows.json').exists():
            with open(data_dir / 'raw_excel_rows.json', 'r', encoding='utf-8') as f:
                for rr in json.load(f):
                    raw = ' | '.join(str(x) if x is not None else '' for x in rr['cells']).strip(' |')
                    cursor.execute(
                        'INSERT INTO raw_excel_rows VALUES(?,?,?)',
                        (rr['source_row'], raw, rr.get('search_text', ''))
                    )

    def optimize(self) -> None:
        """Optimize database."""
        try:
            self.db.analyze()
            self.db.vacuum()
            logger.info("Database optimized")
        except Exception as e:
            logger.warning(f"Optimization failed: {e}")


# Global migration runner instance
_runner = None


def get_migration_runner() -> MigrationRunner:
    """Get or create the global migration runner."""
    global _runner
    if _runner is None:
        _runner = MigrationRunner()
    return _runner
