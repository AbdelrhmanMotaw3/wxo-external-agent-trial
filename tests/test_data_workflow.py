import importlib.util
import unittest
from pathlib import Path

class DataWorkflowTests(unittest.TestCase):
    def test_native_approval_returns_data_result_without_agent_thread_handoff(self):
        path=Path(__file__).resolve().parents[1]/'orchestrate/outage/workflow.py'
        spec=importlib.util.spec_from_file_location('data_flow_contract',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        flow=module.build_outage_credit()
        data=flow.to_json()
        nodes=data['nodes']
        self.assertEqual(nodes['approval']['spec']['kind'],'user_flow')
        self.assertEqual(nodes['record_decision']['spec']['tool'],'kai_outage_workflow_decide')
        self.assertIn('bonus_data_gb',module.Result.model_fields)
        self.assertIn('summary',module.Result.model_fields)
        self.assertNotIn('credit_egp',module.Result.model_fields)
        self.assertFalse(any(node['spec']['kind']=='agent' for node in nodes.values()))
        copilot=path.parent/'agents/copilot.yaml'
        self.assertIn('before starting kai_outage_data_workflow_20261119',copilot.read_text())
