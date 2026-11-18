"""Authenticated synthetic case API; write capability is restricted to workflow."""
import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, StrictBool

from app.auth import require_agent_auth
from app import config
from app.outage import OutageStore, partner_evidence

router = APIRouter(prefix='/outage', tags=['synthetic-outage-demo'])


def store():
    return OutageStore(os.environ.get('OUTAGE_LEDGER_PATH', '/tmp/telco-outage/ledger.db'))


def workflow_auth(authorization: Annotated[str | None, Header()] = None):
    expected = os.environ.get('OUTAGE_WORKFLOW_TOKEN', '')
    if not expected or hmac.compare_digest(expected, config.AGENT_AUTH_TOKEN):
        raise HTTPException(503, 'Separate privileged workflow credential is not configured')
    supplied = (authorization or '').removeprefix('Bearer ')
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(403, 'Workflow capability required')


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quote_id: str
    approved: StrictBool


def invoke(action):
    try:
        return action()
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@router.get('/cases/{case_id}', dependencies=[Depends(require_agent_auth)])
def get_case(case_id: str):
    return invoke(lambda: store().case(case_id))


@router.get('/evidence/{service_id}', dependencies=[Depends(require_agent_auth)])
def get_evidence(service_id: str):
    evidence = partner_evidence(service_id)
    if evidence is None:
        raise HTTPException(404, 'service_not_found')
    return evidence


@router.post('/quotes', dependencies=[Depends(require_agent_auth)])
def prepare_quote(body: QuoteRequest):
    return invoke(lambda: store().quote(body.case_id))


@router.post('/workflow/decide', dependencies=[Depends(workflow_auth)])
def record_workflow_decision(body: DecisionRequest):
    return invoke(lambda: store().decide(body.quote_id, body.approved))
