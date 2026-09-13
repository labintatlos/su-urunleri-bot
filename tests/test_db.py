import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'su_urunleri_bot'))
from tempfile import TemporaryDirectory
from pathlib import Path

import su_urunleri_bot.db as db

class TestDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test.db'
        
        self.original_db_path = db.DB_PATH
        db.DB_PATH = self.db_path
        
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_norm(self):
        self.assertEqual(db.norm('Işık'), 'isik')
        self.assertEqual(db.norm('ÇĞİÖŞÜ'), 'cgiosu')
        self.assertEqual(db.norm('değişiklik'), 'degisiklik')
        
    def test_init_db(self):
        c = db.con()
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        self.assertIn('articles', table_names)
        self.assertIn('rules', table_names)
        c.close()

    def test_search_species(self):
        res = db.search_species('hamsi', kind='commercial')
        self.assertIsInstance(res, list)

if __name__ == '__main__':
    unittest.main()
