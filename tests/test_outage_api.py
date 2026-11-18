import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import outage_api
from app.main import app


class OutageAPITests(unittest.TestCase):
    def test_readers_cannot_apply_and_workflow_revalidates(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            'OUTAGE_LEDGER_PATH': str(Path(temp)/'test.db'),
            'OUTAGE_WORKFLOW_TOKEN': 'privileged-test-workflow-only',
        }), patch('app.config.AGENT_AUTH_TOKEN', 'reader-test-token'):
            with TestClient(app) as client:
                self.assertEqual(client.get('/health').json()['outage_demo_version'], '2026-11-18-en-v2')
                reader = {'Authorization': 'Bearer reader-test-token'}
                writer = {'Authorization': 'Bearer privileged-test-workflow-only'}
                self.assertEqual(client.get('/outage/cases/CASE-NOUR-001').status_code, 401)
                self.assertEqual(client.get('/outage/cases/CASE-NOUR-001', headers=reader).status_code, 200)
                quote = client.post('/outage/quotes', headers=reader, json={'case_id':'CASE-NOUR-001'}).json()
                self.assertEqual(quote['credit_egp'], 90)
                body = {'quote_id':quote['quote_id'], 'approved':True}
                self.assertEqual(client.post('/outage/workflow/decide', headers=reader, json=body).status_code, 403)
                response = client.post('/outage/workflow/decide', headers=writer, json=body)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['invoice_after_egp'], 810)
                self.assertEqual(client.post('/outage/workflow/decide', headers=writer, json={**body,'credit_egp':900}).status_code, 422)

    def test_privileged_endpoint_disabled_without_separate_secret(self):
        with patch.dict(os.environ, {'OUTAGE_WORKFLOW_TOKEN':''}):
            with TestClient(app) as client:
                self.assertEqual(client.post('/outage/workflow/decide', json={
                    'quote_id':'Q-FAKE','approved':True}).status_code, 503)

    def test_resolved_reader_token_cannot_also_be_workflow_token(self):
        from fastapi import HTTPException
        from app import config
        for raw_reader in ('', None):
            with self.subTest(raw_reader=raw_reader), patch.dict(os.environ, {
                'OUTAGE_WORKFLOW_TOKEN':'change-me-trial-token',
            }), patch.object(config, 'AGENT_AUTH_TOKEN', 'change-me-trial-token'):
                if raw_reader is None:
                    os.environ.pop('AGENT_AUTH_TOKEN', None)
                else:
                    os.environ['AGENT_AUTH_TOKEN'] = raw_reader
                with self.assertRaises(HTTPException) as failure:
                    outage_api.workflow_auth('Bearer change-me-trial-token')
                self.assertEqual(failure.exception.status_code, 503)
