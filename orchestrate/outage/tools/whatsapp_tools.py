"""Receipt-grounded WhatsApp staging. No messaging provider is called.

The only network operation is a fresh read through the existing reader capability.
Visible Sent status belongs to the event scenario; metadata records that boundary.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID

from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.run import connections, ToolResult, TextContent, Annotations, Role
from ibm_watsonx_orchestrate.run.context import AgentRun


def _read_case(case_id: str, context: AgentRun) -> dict:
    if case_id != 'CASE-NOUR-001':
        raise ValueError('This notification scene supports CASE-NOUR-001 only.')
    try:
        rehearsal_id = str(UUID(context.request_context.get('wxo_thread_id')))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('A platform conversation ID is required for this notification.') from error
    creds = connections.key_value('kai_outage_reader_20261118')
    base = creds['BASE_URL'].rstrip('/')
    if base != 'https://telecom-network.2gqohspjx3cv.ca-tor.codeengine.appdomain.cloud':
        raise ValueError('Unexpected outage backend.')
    request = Request(base + '/outage/cases/' + quote(case_id, safe=''),
                      headers={'Authorization': 'Bearer ' + creds['TOKEN'],
                               'X-KAI-Rehearsal-ID': rehearsal_id})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('rehearsal_id') != rehearsal_id:
        raise ValueError('The backend did not confirm this conversation rehearsal. Update the session-aware demo backend first.')
    return result


def _money(value) -> Decimal:
    if isinstance(value, bool):
        raise ValueError('Invalid receipt amount.')
    try:
        amount = Decimal(str(value))
    except Exception as error:
        raise ValueError('Invalid receipt amount.') from error
    if not amount.is_finite() or amount < 0:
        raise ValueError('Invalid receipt amount.')
    return amount


def _format_money(value: Decimal) -> str:
    return format(value, 'f').rstrip('0').rstrip('.') if '.' in format(value, 'f') else format(value, 'f')


def prepare_payload(case: dict) -> dict:
    receipt = case.get('credit_receipt') or {}
    if case.get('case_id') != 'CASE-NOUR-001' or case.get('service_id') != 'SVC-NOUR-001' or case.get('synthetic') is not True:
        raise ValueError('Only the configured synthetic customer case is supported.')
    if not (receipt.get('status') == 'applied' and receipt.get('receipt_id')
            and receipt.get('case_id') == case['case_id']
            and receipt.get('human_decision_recorded') is True):
        raise ValueError('A verified posted receipt is required before preparing or sending the update.')
    if case.get('rehearsal_id') and receipt.get('rehearsal_id') != case['rehearsal_id']:
        raise ValueError('The receipt belongs to another conversation rehearsal.')
    credit = _money(receipt.get('credit_egp'))
    before = _money(receipt.get('invoice_before_egp'))
    due = _money(receipt.get('invoice_after_egp'))
    monthly = _money(case.get('monthly_fee_egp'))
    if credit <= 0 or monthly <= 0 or due != _money(case.get('invoice_due_egp')) or before - credit != due:
        raise ValueError('The posted receipt and current invoice do not match. Refresh the case.')
    message = (
        f"Hi Nour, your home internet service has been restored. We have applied a one-time "
        f"service credit of {_format_money(credit)} EGP to case {case['case_id']}. "
        f"Your remaining invoice balance is {_format_money(due)} EGP. "
        f"Your monthly plan remains {_format_money(monthly)} EGP. "
        f"Receipt: {receipt['receipt_id']}. Thank you for your patience. — Aven Customer Care"
    )
    fingerprint = hashlib.sha256(json.dumps([case['case_id'], receipt['receipt_id'], message],
                                            ensure_ascii=False).encode()).hexdigest()[:16]
    return {
        'status': 'draft', 'case_id': case['case_id'], 'service_id': case['service_id'],
        'customer_name': case['customer_name'], 'receipt_id': receipt['receipt_id'],
        'credit_egp': float(credit), 'invoice_after_egp': float(due),
        'monthly_fee_egp': float(monthly), 'draft_id': 'WA-DRAFT-' + fingerprint,
        'message': message, 'channel': 'WhatsApp', 'simulated': True,
        'transport': 'scenario', 'provider_dispatch_performed': False,
        'provider_message_id': None, 'delivery_status': 'not_attempted',
    }


def _recipient(recipient: str) -> tuple[str, str]:
    saved = {'nour_whatsapp', 'nour', 'nour ahmed', "nour's saved whatsapp", 'saved contact'}
    if recipient.strip().lower() in saved:
        return '+201000000000', '+201*********'
    normalized = re.sub(r'[\s()-]', '', recipient.strip())
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', normalized):
        raise ValueError("Choose Nour's saved WhatsApp contact or provide a valid international recipient. A redacted recipient cannot be inferred.")
    return normalized, normalized[:4] + '*' * (len(normalized) - 4)


def _card(title: str, data: dict, fields: dict) -> dict:
    # The native UI dropped the earlier widget. Complete readable content is now
    # the primary contract, so a missing widget can never hide the actual update.
    rows = '\n'.join(f'| {label} | {str(value).replace("|", " / ")} |'
                     for key, (label, value) in fields.items() if key != 'message')
    text = (f'### {title}\n\n| Detail | Value |\n|---|---|\n{rows}'
            f'\n\n**Message**\n\n> {data["message"]}')
    return {
        'content': [{'type': 'text', 'text': text, 'annotations': {'audience': ['user']}}],
        'structuredContent': data,
        '_meta': {'kai_transport_mode': 'scenario', 'provider_dispatch_performed': False},
    }


def _native_result(result: dict) -> ToolResult:
    return ToolResult(content=[TextContent(text=result['content'][0]['text'],
                      annotations=Annotations(audience=[Role.USER]))],
                      structuredContent=result['structuredContent'], meta=result['_meta'])


def preview_response(case: dict) -> dict:
    data = prepare_payload(case)
    return _card('WhatsApp message ready', data, {
        'status': ('Status', 'Draft ready'), 'customer': ('Customer', data['customer_name']),
        'case': ('Case ID', data['case_id']), 'message': ('Message', data['message']),
        'draft': ('Draft reference', data['draft_id']),
        'receipt': ('Credit receipt', data['receipt_id']),
        'next': ('Next step', 'Tell KAI who should receive this update.'),
    })


def dispatch_response(case: dict, draft_id: str, recipient: str) -> dict:
    data = prepare_payload(case)
    if draft_id and draft_id != data['draft_id']:
        raise ValueError('The draft no longer matches the current posted receipt. Prepare the message again.')
    normalized, display = _recipient(recipient)
    reference = hashlib.sha256((data['draft_id'] + '|' + normalized).encode()).hexdigest()[:16]
    data.update(status='sent', message_id='KAI-WA-' + reference,
                recipient=display, sent_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    return _card('WhatsApp sent', data, {
        'status': ('Status', 'Sent'), 'recipient': ('Recipient', display),
        'channel': ('Channel', 'WhatsApp'), 'case': ('Case ID', data['case_id']),
        'reference': ('Message reference', data['message_id']),
        'message': ('Message', data['message']), 'receipt': ('Credit receipt', data['receipt_id']),
    })


@tool(expected_credentials=[ExpectedCredentials(app_id='kai_outage_reader_20261118', type=ConnectionType.KEY_VALUE)],
      description='Prepare the complete English WhatsApp draft from the current conversation receipt. Preparation only; explicit send intent uses kai_outage_whatsapp_send instead. Scenario transport only.')
def kai_outage_whatsapp_preview(case_id: str, context: AgentRun) -> ToolResult:
    """Prepare a receipt-grounded draft. This does not send a message.

    Args:
        case_id: Active case identifier, CASE-NOUR-001.
        context: Platform-injected conversation context.
    """
    return _native_result(preview_response(_read_case(case_id, context)))


@tool(expected_credentials=[ExpectedCredentials(app_id='kai_outage_reader_20261118', type=ConnectionType.KEY_VALUE)],
      description='Use for explicit send intent, including send to WhatsApp. Prepare inline when no draft exists, verify any supplied draft against this conversation receipt, and show the complete Sent result. No provider API or delivery claim.')
def kai_outage_whatsapp_send(case_id: str, context: AgentRun, recipient: str = 'NOUR_WHATSAPP', draft_id: str = '') -> ToolResult:
    """Return the scenario transport result for an explicitly requested dispatch.

    Args:
        case_id: Active case identifier, CASE-NOUR-001.
        context: Platform-injected conversation context.
        draft_id: Exact preview draft_id if available; empty prepares the canonical current message inline for explicit send intent.
        recipient: NOUR_WHATSAPP for Nour's saved contact, or an explicit international number. Redacted values are invalid.
    """
    return _native_result(dispatch_response(_read_case(case_id, context), draft_id, recipient))
