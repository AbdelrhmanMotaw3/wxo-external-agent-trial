"""Authenticated native Draft smoke tests; persist answers and IDs, never reasoning."""
import argparse
import json
import time
from pathlib import Path
import httpx
from ibm_watsonx_orchestrate.client.utils import get_current_env_url, instantiate_client
from ibm_watsonx_orchestrate_clients.agents.agent_client import AgentClient

EXPECTED = 'https://api.au-syd.watson-orchestrate.cloud.ibm.com/instances/cf489b1a-fca3-4013-947f-5ae008b3a3fd'


def run(agent_name, message, thread_id=None, release='draft'):
    if get_current_env_url().rstrip('/') != EXPECTED:
        raise RuntimeError('Activate ISYS-Event-Nov2026 first')
    with httpx.Client(headers=instantiate_client(AgentClient)._get_headers(), timeout=45) as client:
        base = EXPECTED+'/v1/orchestrate'
        response = client.get(base+'/agents')
        response.raise_for_status()
        agents = response.json()
        if isinstance(agents, dict):
            agents = agents.get('agents', agents.get('data', []))
        agent = next(a for a in agents if a['name'] == agent_name)
        payload = {'agent_id': agent['id'], 'message':{'role':'user','content':message}}
        if release == 'live':
            environments = client.get(base+'/agents/'+agent['id']+'/environment')
            environments.raise_for_status()
            rows = environments.json()
            if isinstance(rows, dict):
                rows = rows.get('environments',rows.get('data',[]))
            payload['environment_id'] = next(e['id'] for e in rows if e['name'] == 'live')
        if thread_id:
            payload['thread_id'] = thread_id
        response = client.post(base+'/runs', json=payload)
        response.raise_for_status()
        ids = response.json()
        result = {}
        for _ in range(360):
            response = client.get(base+'/runs/'+ids['run_id'])
            response.raise_for_status()
            result = response.json()
            if result['status'] in ('completed','failed','cancelled','incomplete','requires_action'):
                break
            time.sleep(.5)
        content = result.get('result',{}).get('data',{}).get('message',{}).get('content',[])
        answer = content if isinstance(content,str) else '\n'.join(
            item.get('text','') for item in content if item.get('response_type',item.get('type')) in ('text','conversational_search'))
        events_response = client.get(base+'/runs/'+ids['run_id']+'/events')
        events_response.raise_for_status()
        tool_names = []
        for event in events_response.json():
            if event.get('event') != 'run.step.delta':
                continue
            for detail in event.get('data',{}).get('delta',{}).get('step_details',[]):
                if detail.get('type') == 'tool_response':
                    tool_names.append(detail.get('name'))
        return {'agent': agent_name, 'agent_id':agent['id'], 'run_id':ids['run_id'],
                'thread_id':ids['thread_id'], 'status':result['status'], 'answer':answer,
                'tool_responses':tool_names, 'trace_id':result.get('trace_id'),
                'content_types':[i.get('response_type',i.get('type')) for i in content] if isinstance(content,list) else [type(content).__name__],
                'validation_error': 'empty_assistant_text' if not answer.strip() else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent', default='kai_outage_policy_agent_20261118')
    parser.add_argument('--message', required=True)
    parser.add_argument('--thread')
    parser.add_argument('--release', choices=['draft','live'], default='draft')
    parser.add_argument('--output', default='runtime/native-smoke.json')
    args = parser.parse_args()
    result = run(args.agent, args.message, args.thread, args.release)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
