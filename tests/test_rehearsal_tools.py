"""Tool boundary: scope comes from the platform and must be acknowledged."""
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from ibm_watsonx_orchestrate.run.context import AgentRun

path=Path(__file__).resolve().parents[1]/'orchestrate/outage/tools/read_tools.py'
spec=importlib.util.spec_from_file_location('scoped_read_tools',path)
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
SESSION='11111111-1111-4111-8111-111111111111'


class RehearsalToolTests(unittest.TestCase):
    def test_scoped_read_uses_the_platform_thread_not_a_model_argument(self):
        context=AgentRun(request_context={'wxo_thread_id':SESSION})
        payload={'case_id':'CASE-NOUR-001','rehearsal_id':SESSION,'invoice_due_egp':900}
        with patch.object(reader.connections,'key_value',return_value={'BASE_URL':'https://example.test','TOKEN':'test-only'}), patch.object(reader,'urlopen',return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            result=reader.kai_outage_get_case('CASE-NOUR-001',context=context)
        self.assertEqual(result.content['invoice_due_egp'],900)
        self.assertEqual(dict(request.call_args.args[0].header_items())['X-kai-rehearsal-id'],SESSION)

    def test_missing_context_does_not_fall_back_to_the_shared_case(self):
        with patch.object(reader,'urlopen') as request:
            with self.assertRaisesRegex(ValueError,'conversation ID'):
                reader.kai_outage_get_case('CASE-NOUR-001',context=AgentRun())
        request.assert_not_called()

    def test_old_backend_that_ignores_the_scope_is_rejected(self):
        with patch.object(reader.connections,'key_value',return_value={'BASE_URL':'https://example.test','TOKEN':'test-only'}), patch.object(reader,'urlopen',return_value=io.BytesIO(b'{"case_id":"CASE-NOUR-001","invoice_due_egp":810}')):
            with self.assertRaisesRegex(ValueError,'did not confirm'):
                reader._request('/outage/cases/CASE-NOUR-001',rehearsal_id=SESSION)

    def test_wrong_namespace_in_response_is_rejected(self):
        with patch.object(reader.connections,'key_value',return_value={'BASE_URL':'https://example.test','TOKEN':'test-only'}), patch.object(reader,'urlopen',return_value=io.BytesIO(b'{"rehearsal_id":"22222222-2222-4222-8222-222222222222"}')):
            with self.assertRaisesRegex(ValueError,'did not confirm'):
                reader._request('/outage/cases/CASE-NOUR-001',rehearsal_id=SESSION)


if __name__=='__main__':
    unittest.main()
