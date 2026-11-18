"""Native Flow MCP inspection. Never prints credentials or model reasoning."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from ibm_watsonx_orchestrate.client.utils import instantiate_client, get_current_env_url
from ibm_watsonx_orchestrate.client.tools.flow_mcp_client import FlowMCPClient

FLOW = 'kai_outage_credit_workflow_20261118'
sys.stdout.reconfigure(encoding='utf-8')


def unwrap(result):
    if getattr(result,'isError',False):
        raise RuntimeError('Native MCP operation returned an error')
    structured = getattr(result,'structuredContent',None)
    if structured is not None:
        return structured
    for item in getattr(result,'content',[]):
        if getattr(item,'type',None) == 'text':
            try:
                return json.loads(item.text)
            except ValueError:
                return {'text':item.text}
    return {}


async def main(args):
    if not get_current_env_url().endswith('/instances/cf489b1a-fca3-4013-947f-5ae008b3a3fd'):
        raise RuntimeError('Unexpected Orchestrate tenant')
    client = instantiate_client(FlowMCPClient)
    captured = asyncio.Event()
    async def inspect_form(context, params):
        from mcp import types
        payload = params.model_dump(mode='json', exclude_none=True)
        Path(args.output).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(payload,ensure_ascii=False,indent=2),flush=True)
        captured.set()
        # Keep the real native task pending while the test operator inspects it.
        decision = await asyncio.to_thread(input, 'Test decision (reject/approve): ')
        if decision not in ('reject','approve'):
            return types.ErrorData(code=-32603,message='No test decision submitted')
        return types.ElicitResult(action='accept',content={'approved':decision == 'approve'})
    if args.action == 'form':
        client.set_elicitation_callback(inspect_form)
    async with client:
        if args.action == 'discover':
            tools = await client.list_tools()
            result = [{'name':t.name,'inputSchema':t.inputSchema} for t in tools
                      if 'kai_outage' in t.name or t.name in (
                          'list_flows','subscribe_flow','submit_flow_elicitation')]
        elif args.action == 'start':
            result = unwrap(await client.arun_flow(FLOW,{'case_id':'CASE-NOUR-001'},context={
                'environment_id':'draft','channel_capabilities':['form']}))
        elif args.action == 'query':
            result = unwrap(await client.query_flow(FLOW,args.instance))
        elif args.action == 'details':
            result = unwrap(await client.list_flows(instance_id=args.instance, include_details=True))
        elif args.action == 'form':
            print(json.dumps(unwrap(await client._call_tool('subscribe_flow',{'instance_id':args.instance}))),flush=True)
            print(json.dumps(unwrap(await client.replay_flow_pending_elicitation(args.instance))),flush=True)
            await asyncio.wait_for(captured.wait(),timeout=30)
            # callback blocks on the explicit operator decision above; poll until resumed.
            for _ in range(120):
                await asyncio.sleep(1)
                state = unwrap(await client.list_flows(instance_id=args.instance,include_details=True))
                if state.get('instances',[{}])[0].get('state') in ('completed','failed','cancelled'):
                    result = state
                    break
            else:
                raise TimeoutError('Native task has not reached a terminal state')
        else:
            raise ValueError('Unsupported read/start operation')
    path = Path(args.output)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    visible = result
    if isinstance(result,dict) and 'instances' in result:
        visible = [{'instance_id':row.get('instance_id'),'state':row.get('state'),
                    'output':{key:value for key,value in (row.get('output') or {}).items()
                              if key in ('status','case_id','quote_id','receipt_id','credit_egp','invoice_after_egp')},
                    'error_present':bool(row.get('error'))} for row in result['instances']]
    print(json.dumps(visible,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['discover','start','query','details','form'])
    parser.add_argument('--instance')
    parser.add_argument('--output',default='runtime/flow-probe.json')
    asyncio.run(main(parser.parse_args()))
