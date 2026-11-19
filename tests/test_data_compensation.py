"""The approved event remedy is bonus data, never an invoice adjustment."""
import tempfile
import sqlite3
from contextlib import closing
import unittest
from pathlib import Path
from app.outage import OutageStore

class DataCompensationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.path=Path(self.directory.name)/'ledger.db'
        self.store=OutageStore(self.path,'11111111-1111-4111-8111-111111111111')

    def tearDown(self):
        self.directory.cleanup()

    def test_quote_proposes_20_gb_with_unchanged_invoice(self):
        q=self.store.quote('CASE-NOUR-001')
        self.assertEqual(q.get('bonus_data_gb'),20)
        self.assertEqual(q['invoice_before_egp'],900)
        self.assertEqual(q['invoice_after_egp'],900)
        self.assertEqual(q.get('bonus_balance_before_gb'),0)
        self.assertEqual(q.get('bonus_balance_after_gb'),20)
        self.assertTrue(q['requires_approval'])
        self.assertNotIn('credit_egp',q)
        self.assertEqual(self.store.case('CASE-NOUR-001').get('bonus_data_balance_gb'),0)

    def test_approval_awards_data_once_and_preserves_bill(self):
        q=self.store.quote('CASE-NOUR-001')
        receipt=self.store.decide(q['quote_id'],True)
        case=self.store.case('CASE-NOUR-001')
        self.assertEqual(receipt.get('bonus_data_gb'),20)
        self.assertEqual(case.get('bonus_data_balance_gb'),20)
        self.assertEqual(case['invoice_due_egp'],900)
        self.assertEqual(case.get('compensation_receipt'),receipt)
        self.assertEqual(self.store.decide(q['quote_id'],True),receipt)
        self.assertEqual(self.store.case('CASE-NOUR-001').get('bonus_data_balance_gb'),20)
        self.assertNotIn('credit_receipt',case)

    def test_rejection_and_new_chat_preserve_zero_bonus(self):
        q=self.store.quote('CASE-NOUR-001')
        rejected=self.store.decide(q['quote_id'],False)
        self.assertEqual(rejected.get('bonus_data_gb'),0)
        self.assertEqual(self.store.case('CASE-NOUR-001').get('bonus_data_balance_gb'),0)
        q=self.store.quote('CASE-NOUR-001')
        self.store.decide(q['quote_id'],True)
        other=OutageStore(self.path,'22222222-2222-4222-8222-222222222222').case('CASE-NOUR-001')
        self.assertEqual(other.get('bonus_data_balance_gb'),0)
        self.assertEqual(other['invoice_due_egp'],900)
        self.assertIsNone(other.get('compensation_receipt'))

    def test_historical_financial_case_is_not_reused_or_modified(self):
        old_key='11111111-1111-4111-8111-111111111111:CASE-NOUR-001'
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('INSERT INTO cases VALUES (?,?,?,?,?,?,?)',
                       (old_key,'SVC-NOUR-001','Nour Ahmed','Nour Ahmed',90000,81000,2))
            db.commit()
        current=self.store.case('CASE-NOUR-001')
        self.assertEqual(current['invoice_due_egp'],900)
        self.assertEqual(current['bonus_data_balance_gb'],0)
        self.assertIsNone(current['compensation_receipt'])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT invoice_piasters FROM cases WHERE id=?',(old_key,)).fetchone()[0],81000)
