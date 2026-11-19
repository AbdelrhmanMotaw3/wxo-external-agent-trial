"""Preserve the platform context present in the verified native UI baseline."""
import unittest
from pathlib import Path
import yaml
from ibm_watsonx_orchestrate.agent_builder.agents.types import AgentSpec


class WorkflowContextTests(unittest.TestCase):
    def test_rehearsal_scoping_keeps_native_workflow_resume_context(self):
        path=Path(__file__).resolve().parents[1]/'orchestrate/outage/agents/copilot.yaml'
        spec=AgentSpec.model_validate(yaml.safe_load(path.read_text(encoding='utf-8')))
        # Only thread_id is needed by the ledger. The native UI's previously
        # working form also carried platform run/tenant/actor context.
        required={'wxo_thread_id','wxo_run_id','wxo_tenant_id','wxo_email_id','wxo_user_name'}
        self.assertTrue(spec.context_access_enabled)
        self.assertTrue(required.issubset(spec.context_variables),
                        'Conversation isolation must preserve native workflow resume context')
