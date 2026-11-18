"""Native Orchestrate read capabilities; no privileged workflow credentials."""
import json
from urllib.request import Request, urlopen
from urllib.parse import quote
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ExpectedCredentials, ConnectionType
from ibm_watsonx_orchestrate.run import connections


def _request(path, body=None):
    creds = connections.key_value('kai_outage_reader_20261118')
    base = creds['BASE_URL'].rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('HTTPS backend required')
    request = Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization':'Bearer '+creds['TOKEN'], 'Content-Type':'application/json'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


@tool(expected_credentials=[ExpectedCredentials(app_id='kai_outage_reader_20261118', type=ConnectionType.KEY_VALUE)],
      description='Read the synthetic complaint, cross-channel history, current invoice and posted receipt. اقرأ الشكوى وسجل القنوات والفاتورة.')
def kai_outage_get_case(case_id: str) -> dict:
    """Read case state. Args: case_id: Exact synthetic case identifier."""
    return _request('/outage/cases/'+quote(case_id, safe=''))


@tool(expected_credentials=[ExpectedCredentials(app_id='kai_outage_reader_20261118', type=ConnectionType.KEY_VALUE)],
      description='Prepare a source-backed synthetic credit quote. No invoice change and no approval. احسب عرض التعويض دون تنفيذ.')
def kai_outage_prepare_quote(case_id: str) -> dict:
    """Prepare authoritative quote. Args: case_id: Exact synthetic case identifier."""
    return _request('/outage/quotes', {'case_id':case_id})


