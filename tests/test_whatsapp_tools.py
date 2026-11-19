"""Contract checks for the local-only notification transport inside Orchestrate."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
from ibm_watsonx_orchestrate.run.context import AgentRun

path = Path(__file__).resolve().parents[1] / 'orchestrate/outage/tools/whatsapp_tools.py'
spec = importlib.util.spec_from_file_location('whatsapp_tools', path)
wa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wa)


def posted_case():
    return {
        'case_id': 'CASE-NOUR-001', 'service_id': 'SVC-NOUR-001', 'customer_name': 'Nour Ahmed',
        'synthetic': True, 'monthly_fee_egp': 900, 'invoice_due_egp': 810,
        'credit_receipt': {'case_id': 'CASE-NOUR-001', 'receipt_id': 'CR-TEST-001',
            'status': 'applied', 'human_decision_recorded': True,
            'credit_egp': 90, 'invoice_before_egp': 900, 'invoice_after_egp': 810},
    }


class WhatsAppToolTests(unittest.TestCase):
    def test_primary_native_output_contains_the_full_sent_message(self):
        case = posted_case()
        result = wa.dispatch_response(case, wa.prepare_payload(case)['draft_id'], 'NOUR_WHATSAPP')
        text = result['content'][0]['text']
        self.assertIn(result['structuredContent']['message'], text)
        self.assertIn('+201*********', text)
        self.assertIn(result['structuredContent']['message_id'], text)
        self.assertIn('CASE-NOUR-001', text)

    def test_explicit_send_can_prepare_the_canonical_message_inline(self):
        result = wa.dispatch_response(posted_case(), '', 'NOUR_WHATSAPP')
        self.assertEqual(result['structuredContent']['status'], 'sent')
        self.assertIn('90 EGP', result['structuredContent']['message'])

    def test_inline_send_reference_matches_preview_and_changes_with_receipt(self):
        case = posted_case()
        inline = wa.dispatch_response(case, '', 'NOUR_WHATSAPP')['structuredContent']
        staged = wa.dispatch_response(case, wa.prepare_payload(case)['draft_id'], 'NOUR_WHATSAPP')['structuredContent']
        self.assertEqual(inline['message_id'], staged['message_id'])
        case['credit_receipt']['receipt_id'] = 'CR-NEXT-REHEARSAL'
        other = wa.dispatch_response(case, '', 'NOUR_WHATSAPP')['structuredContent']
        self.assertNotEqual(inline['message_id'], other['message_id'])

    def test_notification_rejects_a_receipt_from_another_rehearsal(self):
        case = posted_case()
        case['rehearsal_id'] = '11111111-1111-4111-8111-111111111111'
        case['credit_receipt']['rehearsal_id'] = '22222222-2222-4222-8222-222222222222'
        with self.assertRaisesRegex(ValueError, 'another conversation'):
            wa.prepare_payload(case)

    def test_unsettled_case_cannot_prepare_or_announce_sent(self):
        case = posted_case()
        case['credit_receipt'] = None
        with self.assertRaisesRegex(ValueError, 'posted receipt'):
            wa.prepare_payload(case)

    def test_preview_uses_actual_receipt_and_exposes_readable_primary_content(self):
        result = wa.preview_response(posted_case())
        data = result['structuredContent']
        self.assertEqual(data['status'], 'draft')
        self.assertIn('90 EGP', data['message'])
        self.assertIn('810 EGP', data['message'])
        self.assertIn('CR-TEST-001', data['message'])
        self.assertEqual(data['provider_message_id'], None)
        self.assertIn('WhatsApp message ready', result['content'][0]['text'])
        self.assertIn(data['message'], result['content'][0]['text'])

    def test_dispatch_requires_the_exact_current_draft(self):
        case = posted_case()
        draft = wa.prepare_payload(case)
        case['credit_receipt']['receipt_id'] = 'CR-NEW-002'
        with self.assertRaisesRegex(ValueError, 'Prepare the message again'):
            wa.dispatch_response(case, draft['draft_id'], 'NOUR_WHATSAPP')

    def test_sent_card_is_grounded_and_never_claims_provider_delivery(self):
        case = posted_case()
        draft = wa.prepare_payload(case)
        result = wa.dispatch_response(case, draft['draft_id'], 'NOUR_WHATSAPP')
        data = result['structuredContent']
        self.assertEqual(data['message'], draft['message'])
        self.assertEqual(data['status'], 'sent')
        self.assertTrue(data['simulated'])
        self.assertFalse(data['provider_dispatch_performed'])
        self.assertIsNone(data['provider_message_id'])
        self.assertEqual(data['delivery_status'], 'not_attempted')
        self.assertTrue(data['message_id'].startswith('KAI-WA-'))
        self.assertEqual(data['recipient'], '+201*********')
        self.assertIn('WhatsApp sent', result['content'][0]['text'])
        self.assertNotIn('+201000000000', str(result))

    def test_card_exposes_only_a_masked_phone_prefix(self):
        case = posted_case()
        result = wa.dispatch_response(case, wa.prepare_payload(case)['draft_id'], '+20 111 111 1111')
        recipient = result['structuredContent']['recipient']
        self.assertEqual(recipient, '+201*********')
        self.assertIn(recipient, result['content'][0]['text'])
        self.assertNotIn('+201111111111', str(result))

    def test_same_draft_and_recipient_have_a_stable_reference(self):
        case = posted_case()
        draft = wa.prepare_payload(case)
        first = wa.dispatch_response(case, draft['draft_id'], 'NOUR_WHATSAPP')['structuredContent']
        again = wa.dispatch_response(case, draft['draft_id'], 'Nour Ahmed')['structuredContent']
        self.assertEqual(first['message_id'], again['message_id'])
        other = wa.dispatch_response(case, draft['draft_id'], '+201111111111')['structuredContent']
        self.assertNotEqual(first['message_id'], other['message_id'])

    def test_redacted_or_invalid_recipient_is_not_silently_substituted(self):
        for recipient in ('[REDACTED]', '', 'invalid', '+000'):
            with self.subTest(recipient=recipient), self.assertRaises(ValueError):
                wa.dispatch_response(posted_case(), wa.prepare_payload(posted_case())['draft_id'], recipient)

    def test_stale_balance_or_forged_case_receipt_cannot_be_sent(self):
        for edit in (lambda c: c.update(invoice_due_egp=900),
                     lambda c: c['credit_receipt'].update(case_id='OTHER'),
                     lambda c: c['credit_receipt'].update(human_decision_recorded=False),
                     lambda c: c.update(synthetic=False)):
            case = copy.deepcopy(posted_case())
            edit(case)
            with self.assertRaises(ValueError):
                wa.prepare_payload(case)

    def test_tool_reads_current_case_on_every_send(self):
        draft = wa.prepare_payload(posted_case())
        context = AgentRun(request_context={'wxo_thread_id':'11111111-1111-4111-8111-111111111111'})
        with patch.object(wa, '_read_case', return_value=posted_case()) as reader:
            result = wa.kai_outage_whatsapp_send(case_id='CASE-NOUR-001',context=context,
                                               draft_id=draft['draft_id'],recipient='NOUR_WHATSAPP')
        reader.assert_called_once_with('CASE-NOUR-001',context)
        self.assertEqual(result.structuredContent['receipt_id'], 'CR-TEST-001')
        self.assertIn(result.structuredContent['message'], result.content[0].text)


if __name__ == '__main__':
    unittest.main()
