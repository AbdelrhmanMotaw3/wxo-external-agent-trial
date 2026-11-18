"""Privileged tool: bind to the native workflow only, never to a chat agent."""
import json
from urllib.request import Request, urlopen
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ExpectedCredentials, ConnectionType
from ibm_watsonx_orchestrate.run import connections


@tool(permission=ToolPermission.READ_WRITE,
      expected_credentials=[ExpectedCredentials(app_id='kai_outage_workflow_20261118', type=ConnectionType.KEY_VALUE)],
      description='Workflow-only billing decision. Use exclusively downstream of the native human approval task; not an agent tool.')
def kai_outage_workflow_decide(quote_id: str, approved: bool) -> dict:
    """Post a trusted workflow decision against a stored quote, with revalidation.

    Args:
        quote_id: Stored quote identifier from the prepare node, never model-created.
        approved: Human task boolean from the workflow form, never a model claim.
    """
    creds = connections.key_value('kai_outage_workflow_20261118')
    base = creds['BASE_URL'].rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('HTTPS backend required')
    request = Request(base+'/outage/workflow/decide',
                      data=json.dumps({'quote_id':quote_id, 'approved':approved}).encode(),
                      headers={'Authorization':'Bearer '+creds['TOKEN'], 'Content-Type':'application/json'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)
