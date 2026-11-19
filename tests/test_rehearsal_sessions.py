"""Independent filming takes share case labels, never settlement state."""
import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from app.outage import OutageStore

A = '11111111-1111-4111-8111-111111111111'
B = '22222222-2222-4222-8222-222222222222'


class RehearsalSessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'rehearsals.db'

    def tearDown(self):
        self.directory.cleanup()

    def store(self, session):
        return OutageStore(self.path, rehearsal_id=session)

    def test_new_chats_start_at_900_and_approval_does_not_cross_chats(self):
        first, second = self.store(A), self.store(B)
        self.assertEqual(first.case('CASE-NOUR-001')['invoice_due_egp'], 900)
        self.assertEqual(first.case('CASE-NOUR-001')['bonus_data_balance_gb'],0)
        self.assertEqual(second.case('CASE-NOUR-001')['bonus_data_balance_gb'],0)
        self.assertEqual(second.case('CASE-NOUR-001')['invoice_due_egp'], 900)
        quote = first.quote('CASE-NOUR-001')
        # A workflow callback resolves the stored quote's namespace, independent
        # of a collaborator's changed thread context.
        result = OutageStore(self.path).decide(quote['quote_id'], True)
        self.assertEqual(result['case_id'], 'CASE-NOUR-001')
        self.assertEqual(result['invoice_after_egp'], 900)
        self.assertEqual(first.case('CASE-NOUR-001')['bonus_data_balance_gb'],20)
        self.assertEqual(first.case('CASE-NOUR-001')['invoice_due_egp'], 900)
        self.assertEqual(second.case('CASE-NOUR-001')['invoice_due_egp'], 900)
        self.assertIsNone(second.case('CASE-NOUR-001')['compensation_receipt'])

    def test_same_chat_survives_reopening_and_cannot_get_two_credits(self):
        first = self.store(A)
        quote = first.quote('CASE-NOUR-001')
        receipt = first.decide(quote['quote_id'], True)
        reopened = self.store(A)
        self.assertEqual(reopened.case('CASE-NOUR-001')['invoice_due_egp'], 900)
        self.assertEqual(reopened.case('CASE-NOUR-001')['bonus_data_balance_gb'],20)
        self.assertEqual(reopened.case('CASE-NOUR-001')['compensation_receipt']['receipt_id'], receipt['receipt_id'])
        with self.assertRaisesRegex(ValueError, 'compensation_already_applied'):
            reopened.quote('CASE-NOUR-001')

    def test_pending_approval_in_a_cannot_settle_b(self):
        first, second = self.store(A), self.store(B)
        quote = first.quote('CASE-NOUR-001')
        with self.assertRaisesRegex(ValueError, 'rehearsal_mismatch'):
            second.decide(quote['quote_id'], True)
        self.assertIsNone(second.case('CASE-NOUR-001')['compensation_receipt'])
        self.assertIsNone(first.case('CASE-NOUR-001')['compensation_receipt'])
        first.decide(quote['quote_id'], True)
        self.assertEqual(second.case('CASE-NOUR-001')['invoice_due_egp'], 900)

    def test_reject_then_approve_is_independent_in_each_chat(self):
        for session in (A, B):
            current = self.store(session)
            rejected = current.quote('CASE-NOUR-001')
            self.assertEqual(current.decide(rejected['quote_id'], False)['invoice_after_egp'], 900)
            approved = current.quote('CASE-NOUR-001')
            self.assertEqual(current.decide(approved['quote_id'], True)['invoice_after_egp'], 900)

    def test_concurrent_takes_each_apply_once_with_distinct_receipts(self):
        def complete(session):
            current = self.store(session)
            quote = current.quote('CASE-NOUR-001')
            return current.decide(quote['quote_id'], True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(complete, (A, B)))
        self.assertEqual([row['bonus_data_gb'] for row in results], [20, 20])
        self.assertNotEqual(results[0]['receipt_id'], results[1]['receipt_id'])

    def test_public_identifiers_and_history_remain_unchanged(self):
        case = self.store(A).case('CASE-NOUR-001')
        self.assertEqual(case['case_id'], 'CASE-NOUR-001')
        self.assertEqual(case['service_id'], 'SVC-NOUR-001')
        self.assertEqual(case['rehearsal_id'], A)
        self.assertEqual(case['history'][1]['ref'], 'CASE-NOUR-001')
        quote = self.store(A).quote('CASE-NOUR-001')
        self.assertEqual(quote['case_id'], 'CASE-NOUR-001')
        self.assertEqual(quote['rehearsal_id'], A)

    def test_existing_unscoped_case_remains_separate(self):
        legacy = OutageStore(self.path)
        quote = legacy.quote('CASE-NOUR-001')
        legacy.decide(quote['quote_id'], True)
        self.assertEqual(self.store(A).case('CASE-NOUR-001')['invoice_due_egp'], 900)
        self.assertEqual(legacy.case('CASE-NOUR-001')['invoice_due_egp'], 900)

    def test_arbitrary_paths_and_malformed_namespaces_are_rejected(self):
        for value in ('', '../other.db', 'shared', 'not-a-uuid', A + ':CASE-NOUR-001'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store(value)


if __name__ == '__main__':
    unittest.main()
