import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'su_urunleri_bot'))

from su_urunleri_bot.screens import (
    progress_bar,
    trend_bar,
    audit_rule_length,
    tally
)

class DummyContext:
    def __init__(self, data):
        self.user_data = data

class TestScreensBusinessLogic(unittest.TestCase):
    def test_progress_bar(self):
        self.assertEqual(progress_bar(3, 12, width=10), '▰▰▱▱▱▱▱▱▱▱  3/12')
        self.assertEqual(progress_bar(0, 5, width=5), '▱▱▱▱▱  0/5')
        self.assertEqual(progress_bar(5, 5, width=5), '▰▰▰▰▰  5/5')
    
    def test_trend_bar(self):
        self.assertEqual(trend_bar(5, 10, width=10), '▰▰▰▰▰▱▱▱▱▱ 5')
    
    def test_tally(self):
        res = tally(['ok', 'bad', 'skip', None, 'ok'])
        self.assertEqual(res, '✅ 2  ·  ❌ 1  ·  ⚪ 1  ·  ⋯ 1')

    def test_audit_rule_length(self):
        ctx1 = DummyContext({'audit_length_exact': 15})
        self.assertEqual(audit_rule_length(ctx1), 15.0)

        ctx2 = DummyContext({'audit_length_band': '12to22'})
        self.assertEqual(audit_rule_length(ctx2), 17.0)

        ctx3 = DummyContext({'audit_length': 25})
        self.assertEqual(audit_rule_length(ctx3), 25.0)

if __name__ == '__main__':
    unittest.main()
