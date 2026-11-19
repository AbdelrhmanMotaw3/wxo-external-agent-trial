"""Activate the reviewed 20 GB package after the matching backend release.

Run from this checkout in the authenticated ISYS-Event-Nov2026 CLI environment.
No credentials are read, printed or changed; the full demo is not published Live.
"""
import json
import subprocess
from pathlib import Path
from urllib.request import urlopen
import yaml
from ibm_watsonx_orchestrate.client.utils import instantiate_client, get_current_env_url
from ibm_watsonx_orchestrate_clients.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate_clients.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate_clients.knowledge_bases.knowledge_base_client import KnowledgeBaseClient

ROOT=Path(__file__).resolve().parents[1]
BASE='https://telecom-network.2gqohspjx3cv.ca-tor.codeengine.appdomain.cloud'
COPILOT='c8554126-9c11-4f6f-b5cb-8c70a663d4f6'
POLICY='852b8c51-bf00-4263-a2d6-c2d3af3cdf0a'
COMMS='58f0fdd5-8cda-46ac-bdc1-7898ba899196'
WRITER='3867c7d8-397b-4c75-94e8-92747396369a'
OLD_FLOWS={'816ee243-dfca-4c61-870c-449971fefc5b','fa7ab96e-be92-48f8-90e6-d4b91141dc0d',
           '07c9af63-3a59-44a5-8c24-c6cdb5dc0a70'}

def main():
    assert get_current_env_url().endswith('/cf489b1a-fca3-4013-947f-5ae008b3a3fd')
    with urlopen(BASE+'/health',timeout=30) as response: health=json.load(response)
    assert health.get('outage_demo_version')=='2026-11-19-data-v4'
    assert health.get('compensation_type')=='bonus_data' and health.get('compensation_gb')==20
    assert health.get('rehearsal_sessions') is True
    agents=instantiate_client(AgentClient);tools=instantiate_client(ToolClient)
    knowledge=instantiate_client(KnowledgeBaseClient)
    kb=knowledge.get_by_name('kai_outage_data_policy_20261119')
    status=knowledge.status(kb['id'])
    assert status.get('ready') is True and status.get('built_in_index_status')=='ready'
    # The CLI status was already verified; retain its fresh machine response.
    (ROOT/'runtime/data-kb-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    flow=next(row for row in tools.get_draft_by_name('kai_outage_data_workflow_20261119')
              if row['name']=='kai_outage_data_workflow_20261119')
    before={aid:agents.get_draft_by_id(aid) for aid in (COPILOT,POLICY,COMMS)}
    backup=ROOT/'runtime/data-draft-agent-rollback.json'
    if not backup.exists():
        backup.write_text(json.dumps({aid:{key:r.get(key) for key in ('id','tools','instructions',
            'description','display_name','knowledge_base','context_access_enabled','context_variables')}
            for aid,r in before.items()},indent=2),encoding='utf-8')
    assert WRITER not in before[COPILOT]['tools']
    for source,connection in (('read_tools.py','kai_outage_reader_20261118'),
                              ('whatsapp_tools.py','kai_outage_reader_20261118'),
                              ('workflow_tools.py','kai_outage_workflow_20261118')):
        result=subprocess.run(['orchestrate','tools','import','-k','python','-f',
            str(ROOT/'orchestrate/outage/tools'/source),'-r',
            str(ROOT/'orchestrate/outage/tools/requirements.txt'),'-a',connection],
            cwd=ROOT,capture_output=True,text=True)
        if result.returncode: raise RuntimeError('Draft tool import failed: '+source)
        print(json.dumps({'phase':'tool_updated','source':source}),flush=True)
    for aid,file in ((POLICY,'policy.yaml'),(COMMS,'communications.yaml')):
        spec=yaml.safe_load((ROOT/'orchestrate/outage/agents'/file).read_text(encoding='utf-8'))
        patch={key:spec[key] for key in ('display_name','description','instructions')}
        if aid==POLICY:patch['knowledge_base']=[kb['id']]
        agents.update(aid,patch)
    spec=yaml.safe_load((ROOT/'orchestrate/outage/agents/copilot.yaml').read_text(encoding='utf-8'))
    bound=[tid for tid in before[COPILOT]['tools'] if tid not in OLD_FLOWS]
    bound=list(dict.fromkeys(bound+[flow['id']]))
    agents.update(COPILOT,{'description':spec['description'],'instructions':spec['instructions'],
        'tools':bound,'context_access_enabled':True,'context_variables':spec['context_variables']})
    after=agents.get_draft_by_id(COPILOT)
    assert flow['id'] in after['tools'] and not OLD_FLOWS.intersection(after['tools'])
    assert WRITER not in after['tools']
    assert after['collaborators']==before[COPILOT]['collaborators']
    assert agents.get_draft_by_id(POLICY)['knowledge_base']==[kb['id']]
    result={'phase':'data_draft_ready','workflow_id':flow['id'],'knowledge_base_id':kb['id'],
            'bonus_data_gb':20,'invoice_egp':900,'live_published':False,
            'native_ui_submit_verified':False}
    (ROOT/'runtime/data-draft-activation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
