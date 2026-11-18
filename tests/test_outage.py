"""Business acceptance: synthetic outage, human decisions and single credit."""
import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from app import outage


class OutageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'ledger.sqlite3'
        self.store = outage.OutageStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_confirmed_partner_evidence_and_channel_history(self):
        case = self.store.case('CASE-NOUR-001')
        self.assertEqual(case['monthly_fee_egp'], 900)
        self.assertEqual([e['channel'] for e in case['history']], ['kiosk', 'website', 'employee'])
        evidence = outage.partner_evidence(case['service_id'])
        self.assertEqual(evidence['confirmed_hours'], 72)
        self.assertEqual(evidence['status'], 'restored')
        self.assertEqual(evidence['cause'], 'provider_network_fault')
        self.assertTrue(evidence['source_ref'])
        self.assertNotIn('credit_egp', evidence)

    def test_quote_is_not_a_credit(self):
        quote = self.store.quote('CASE-NOUR-001')
        self.assertEqual(quote['credit_egp'], 90)
        self.assertEqual(quote['invoice_after_egp'], 810)
        self.assertTrue(quote['requires_approval'])
        self.assertEqual(self.store.case('CASE-NOUR-001')['invoice_due_egp'], 900)

    def test_rejection_never_changes_invoice(self):
        quote = self.store.quote('CASE-NOUR-001')
        result = self.store.decide(quote['quote_id'], False)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(self.store.case('CASE-NOUR-001')['invoice_due_egp'], 900)
        with self.assertRaises(ValueError):
            self.store.decide(quote['quote_id'], True)

    def test_approved_once_even_with_concurrent_retries_and_restart(self):
        quote = self.store.quote('CASE-NOUR-001')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(lambda _: self.store.decide(quote['quote_id'], True), range(4)))
        self.assertEqual(len({r['receipt_id'] for r in receipts}), 1)
        fresh = outage.OutageStore(self.path)
        self.assertEqual(fresh.case('CASE-NOUR-001')['invoice_due_egp'], 810)
        self.assertEqual(fresh.case('CASE-NOUR-001')['monthly_fee_egp'], 900)
        self.assertEqual(fresh.decide(quote['quote_id'], True)['receipt_id'], receipts[0]['receipt_id'])

    def test_different_quotes_cannot_duplicate_credit(self):
        a = self.store.quote('CASE-NOUR-001')
        b = self.store.quote('CASE-NOUR-001')
        self.store.decide(a['quote_id'], True)
        with self.assertRaises(ValueError):
            self.store.decide(b['quote_id'], True)

    def test_rejecting_another_quote_reports_current_invoice(self):
        a = self.store.quote('CASE-NOUR-001')
        b = self.store.quote('CASE-NOUR-001')
        self.store.decide(a['quote_id'], True)
        rejection = self.store.decide(b['quote_id'], False)
        self.assertEqual(rejection['invoice_after_egp'], 810)
        self.assertEqual(rejection['invoice_after_egp'], self.store.case('CASE-NOUR-001')['invoice_due_egp'])

    def test_unknown_and_non_provider_fault_are_not_eligible(self):
        self.assertIsNone(outage.partner_evidence('NOT-A-SERVICE'))
        with self.assertRaises(KeyError):
            self.store.case('missing')
        with self.assertRaises(ValueError):
            self.store.quote('CASE-ROUTER-002')

    def test_expired_quote_is_rejected(self):
        quote = self.store.quote('CASE-NOUR-001', now=0)
        with self.assertRaises(ValueError):
            self.store.decide(quote['quote_id'], True, now=3600)


if __name__ == '__main__':
    unittest.main()
