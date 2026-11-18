"""Acceptance checks for the English-only demonstration contract."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from app.outage import OutageStore

ROOT = Path(__file__).resolve().parents[1]
ARABIC = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')


class EnglishDemoTests(unittest.TestCase):
    def test_case_has_one_english_customer_name_and_english_history(self):
        with tempfile.TemporaryDirectory() as directory:
            case = OutageStore(Path(directory)/'ledger.db').case('CASE-NOUR-001')
        self.assertEqual(case['customer_name'], 'Nour Ahmed')
        self.assertNotIn('customer_ar', case)
        self.assertNotIn('customer_en', case)
        self.assertEqual(case['invoice_due_egp'], 900)
        self.assertIsNone(case['credit_receipt'])
        self.assertIsNone(ARABIC.search(json.dumps(case, ensure_ascii=False)))

    def test_active_demo_sources_contain_no_arabic_text(self):
        files = list((ROOT/'app').rglob('*.py'))
        files += [path for path in (ROOT/'orchestrate/outage').rglob('*')
                  if path.is_file() and path.suffix in ('.py','.yaml','.txt','.json','.md')
                  and 'private' not in path.relative_to(ROOT).parts]
        invalid = [str(path.relative_to(ROOT)) for path in files
                   if ARABIC.search(path.read_text(encoding='utf-8-sig'))]
        self.assertEqual(invalid, [], 'Active demo files still contain Arabic text')


if __name__ == '__main__':
    unittest.main()
