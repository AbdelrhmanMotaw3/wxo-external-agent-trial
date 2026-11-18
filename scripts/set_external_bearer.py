"""User-operated A2A bearer setup with a hidden prompt; no credential file.

Secrets remain in memory during the authorized Orchestrate-to-Orchestrate setup.
Only non-secret registration evidence is persisted.
"""
import json
import getpass
import sys
import warnings
from pathlib import Path
import httpx
import yaml

from ibm_watsonx_orchestrate.agent_builder.agents import ExternalAgent
from ibm_watsonx_orchestrate.client.utils import get_current_env_url, instantiate_client
from ibm_watsonx_orchestrate_clients.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate_clients.agents.agent_client import AgentClient

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 'https://api.au-syd.watson-orchestrate.cloud.ibm.com/instances/cf489b1a-fca3-4013-947f-5ae008b3a3fd'
BASE = 'https://telecom-network.2gqohspjx3cv.ca-tor.codeengine.appdomain.cloud'
EXTERNAL = 'kai_outage_network_partner_20261118'
COPILOT = 'kai_outage_case_copilot_20261118'


def main():
    if get_current_env_url().rstrip('/') != EXPECTED:
        raise RuntimeError('Unexpected Orchestrate tenant')
    if not sys.stdin.isatty():
        raise RuntimeError('Run interactively in your own terminal; do not pipe a token')
    with warnings.catch_warnings():
        # Fail closed if the terminal cannot provide a hidden prompt.
        warnings.simplefilter('error', getpass.GetPassWarning)
        token = getpass.getpass('AGENT_AUTH_TOKEN (hidden; not OUTAGE_WORKFLOW_TOKEN): ').strip()
    if not token or token.startswith('Bearer '):
        raise RuntimeError('Enter only the existing raw AGENT_AUTH_TOKEN')
    # Verify the existing reader's scope without changing any invoice.
    with httpx.Client(timeout=45) as http:
        check = http.get(BASE+'/outage/cases/CASE-NOUR-001', headers={'Authorization':'Bearer '+token})
        if check.status_code != 200:
            raise RuntimeError('Saved reader capability did not authenticate')
    public_spec = yaml.safe_load((ROOT/'orchestrate/outage/external.template.yaml').read_text(encoding='utf-8'))
    public_spec['api_url'] = BASE
    public_spec['auth_config'] = {'token':token}
    spec = ExternalAgent.model_validate(public_spec)
    external = instantiate_client(ExternalAgentClient)
    existing = external.get_draft_by_name(EXTERNAL)
    if len(existing) > 1:
        raise RuntimeError('Ambiguous external registration')
    payload = spec.model_dump(exclude_none=True, mode='json')
    if existing:
        external.update(existing[0]['id'], payload)
    else:
        external.create(payload)
    registered = external.get_draft_by_name(EXTERNAL)
    if len(registered) != 1:
        raise RuntimeError('External registration could not be verified')
    external_id = registered[0]['id']
    native = instantiate_client(AgentClient)
    current = native.get_draft_by_name(COPILOT)
    if len(current) != 1:
        raise RuntimeError('Ambiguous employee copilot')
    current = current[0]
    collaborators = list(current.get('collaborators') or [])
    if external_id not in collaborators:
        collaborators.append(external_id)
    # Routing behavior is authored in the copilot source. Credential setup only
    # attaches the collaborator and preserves the current employee instructions.
    native.update(current['id'], {'collaborators':collaborators})
    evidence = {'external_name':EXTERNAL,'external_id':external_id,'copilot_id':current['id'],
                'endpoint':BASE,'protocol':'A2A/0.3.0','registered':True,'runtime_verified':False}
    path = ROOT/'runtime/external-registration.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception as error:
        # Never echo API error bodies or the external registration payload.
        print(json.dumps({'status':'stopped','error_type':type(error).__name__}))
        raise SystemExit(1)
