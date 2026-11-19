"""Native Orchestrate read capabilities; no privileged workflow credentials."""
import json
from urllib.request import Request, urlopen
from urllib.parse import quote
from uuid import UUID
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ExpectedCredentials, ConnectionType
from ibm_watsonx_orchestrate.run import connections
from ibm_watsonx_orchestrate.run.context import AgentRun


def _rehearsal_id(context: AgentRun) -> str:
    try:
        return str(UUID(context.request_context.get('wxo_thread_id')))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('A platform conversation ID is required for this rehearsal.') from error


def _request(path, body=None, rehearsal_id=None):
    if rehearsal_id is None:
        raise ValueError('A conversation rehearsal is required; shared-ledger fallback is disabled.')
    creds = connections.key_value('kai_outage_reader_20261118')
    base = creds['BASE_URL'].rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('HTTPS backend required')
    request = Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization':'Bearer '+creds['TOKEN'], 'Content-Type':'application/json',
                               'X-KAI-Rehearsal-ID':rehearsal_id})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('rehearsal_id') != rehearsal_id:
        raise ValueError('The backend did not confirm this conversation rehearsal. Update the session-aware demo backend first.')
    return result


@tool(expected_credentials=[ExpectedCredentials(app_id='kai_outage_reader_20261118', type=ConnectionType.KEY_VALUE)],
      description='Read the customer case, channel history, current invoice and posted service-credit receipt.')
def kai_outage_get_case(case_id: str, context: AgentRun) -> dict:
    """Read the case in the current conversation's independent rehearsal.

    Args:
        case_id: Exact synthetic case identifier.
        context: Platform-injected conversation context.
    """
    return _request('/outage/cases/'+quote(case_id, safe=''), rehearsal_id=_rehearsal_id(context))


@tool(expected_credentials=[ExpectedCredentials(app_id='kai_outage_reader_20261118', type=ConnectionType.KEY_VALUE)],
      description='Prepare an evidence-backed service-credit proposal for review. The invoice is changed only by the approved workflow.')
def kai_outage_prepare_quote(case_id: str, context: AgentRun) -> dict:
    """Prepare a quote bound to the current conversation's rehearsal.

    Args:
        case_id: Exact synthetic case identifier.
        context: Platform-injected conversation context.
    """
    return _request('/outage/quotes', {'case_id':case_id}, rehearsal_id=_rehearsal_id(context))


