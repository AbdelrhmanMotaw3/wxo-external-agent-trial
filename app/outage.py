"""Synthetic event ledger. Retail decisions never accept model-supplied amounts."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path

POLICY = 'OUTAGE-DATA-2026.11-v1'
BONUS_DATA_GB = 20
SNAPSHOT = '2026-11-18T12:00:00Z'
EVIDENCE = {
    'SVC-NOUR-001': {
        'incident_id': 'INC-PARTNER-721', 'service_id': 'SVC-NOUR-001',
        'start_utc': '2026-11-14T08:00:00Z', 'restored_utc': '2026-11-17T08:00:00Z',
        'status': 'restored', 'cause': 'provider_network_fault', 'planned': False,
        'scope': 'area', 'provider': 'Demo Network Partner',
        'source_ref': 'partner-network/INC-PARTNER-721/revision-1',
    },
    'SVC-ROUTER-002': {
        'incident_id': 'INC-ROUTER-722', 'service_id': 'SVC-ROUTER-002',
        'start_utc': '2026-11-16T08:00:00Z', 'restored_utc': '2026-11-17T08:00:00Z',
        'status': 'restored', 'cause': 'customer_router_fault', 'planned': False,
        'scope': 'individual', 'provider': 'Demo Network Partner',
        'source_ref': 'partner-network/INC-ROUTER-722/revision-1',
    },
}


def partner_evidence(service_id: str) -> dict | None:
    """Authoritative synthetic partner evidence, not a retail eligibility decision."""
    record = deepcopy(EVIDENCE.get(service_id.strip().upper()))
    if record is None:
        return None
    start = datetime.fromisoformat(record['start_utc'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(record['restored_utc'].replace('Z', '+00:00'))
    record.update(confirmed_hours=(end-start).total_seconds()/3600, synthetic=True, snapshot_utc=SNAPSHOT)
    return record


class OutageStore:
    """SQLite transactions survive process restart when the same disk is retained.

    Code Engine's default local disk is ephemeral: use a persistent backend for
    continuity across revisions/scale-to-zero. Synthetic bonus data; no provisioning rail.
    """
    def __init__(self, path: str | Path, rehearsal_id: str | None = None):
        if rehearsal_id is not None:
            try:
                rehearsal_id = str(uuid.UUID(rehearsal_id))
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError('invalid_rehearsal_id') from error
        self.rehearsal_id = rehearsal_id
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY, service_id TEXT NOT NULL, name_ar TEXT NOT NULL,
                    name_en TEXT NOT NULL, monthly_piasters INTEGER NOT NULL,
                    invoice_piasters INTEGER NOT NULL, version INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS data_quotes (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL, payload TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending', receipt TEXT);
                CREATE TABLE IF NOT EXISTS data_awards (
                    case_id TEXT PRIMARY KEY, quote_id TEXT UNIQUE NOT NULL, receipt TEXT NOT NULL);
            ''')
            db.executemany('INSERT OR IGNORE INTO cases VALUES (?,?,?,?,?,?,1)', [
                (self._case_key('CASE-NOUR-001'), 'SVC-NOUR-001', 'Nour Ahmed', 'Nour Ahmed', 90000, 90000),
                (self._case_key('CASE-ROUTER-002'), 'SVC-ROUTER-002', 'Ahmed Ali', 'Ahmed Ali', 90000, 90000),
            ])

    def _case_key(self, case_id: str) -> str:
        # Private storage namespace only; public customer/case labels stay stable.
        scope = f'{self.rehearsal_id}:{case_id}' if self.rehearsal_id else case_id
        # Keep the new data remedy separate from historical financial rehearsals.
        return f'data-v1:{scope}'

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def case(self, case_id: str) -> dict:
        key = self._case_key(case_id)
        with self._db() as db:
            row = db.execute('SELECT * FROM cases WHERE id=?', (key,)).fetchone()
            award = db.execute('SELECT receipt FROM data_awards WHERE case_id=?', (key,)).fetchone()
        if row is None:
            raise KeyError('case_not_found')
        return {
            'case_id': case_id, 'service_id': row['service_id'],
            'rehearsal_id': self.rehearsal_id,
            # Retain the storage layout for existing ledgers; expose one name.
            'customer_name': row['name_en'],
            'monthly_fee_egp': row['monthly_piasters']/100,
            'invoice_due_egp': row['invoice_piasters']/100, 'invoice_status': 'unpaid',
            'version': row['version'], 'synthetic': True,
            'history': [
                {'channel': 'kiosk', 'event': 'Home internet activated', 'ref': 'ORDER-KAI-2048'},
                {'channel': 'website', 'event': 'Internet outage reported', 'ref': case_id},
                {'channel': 'employee', 'event': 'Case review requested', 'ref': case_id},
            ],
            'bonus_data_balance_gb': json.loads(award['receipt'])['bonus_balance_after_gb'] if award else 0,
            'compensation_receipt': json.loads(award['receipt']) if award else None,
        }

    @staticmethod
    def _assessment(case: dict) -> dict:
        evidence = partner_evidence(case['service_id'])
        if not evidence or evidence['status'] != 'restored' or evidence['cause'] != 'provider_network_fault' or evidence['planned']:
            raise ValueError('not_eligible_for_outage_compensation')
        hours = evidence['confirmed_hours']
        # The fictional event policy grants a fixed one-time data bundle.
        if hours < 24 or hours != int(hours):
            raise ValueError('unsupported_or_insufficient_duration')
        return {'policy_version': POLICY, 'policy_sections': ['S1', 'S2', 'S3', 'S4'],
                'confirmed_hours': hours, 'bonus_data_gb': BONUS_DATA_GB,
                'bonus_balance_before_gb': case['bonus_data_balance_gb'],
                'bonus_balance_after_gb': case['bonus_data_balance_gb'] + BONUS_DATA_GB,
                'invoice_before_egp': case['invoice_due_egp'],
                'invoice_after_egp': case['invoice_due_egp'],
                'requires_approval': True, 'evidence': evidence,
                'invoice_version': case['version'], 'case_id': case['case_id'],
                'synthetic': True, 'adjustment_type': 'bonus_data_bundle'}

    def quote(self, case_id: str, now: float | None = None) -> dict:
        case = self.case(case_id)
        if case['compensation_receipt']:
            raise ValueError('compensation_already_applied')
        payload = self._assessment(case)
        payload.update(quote_id='Q-'+uuid.uuid4().hex[:16], expires_at=(time.time() if now is None else now)+1800)
        if self.rehearsal_id:
            payload['rehearsal_id'] = self.rehearsal_id
        payload['evidence_digest'] = hashlib.sha256(json.dumps(payload['evidence'], sort_keys=True).encode()).hexdigest()
        with self._db() as db:
            db.execute('INSERT INTO data_quotes(id,case_id,payload) VALUES (?,?,?)',
                       (payload['quote_id'], self._case_key(case_id), json.dumps(payload, ensure_ascii=False)))
        return payload

    def decide(self, quote_id: str, approved: bool, now: float | None = None) -> dict:
        """Privileged workflow-only operation; caller authentication lives at HTTP seam."""
        if type(approved) is not bool:
            raise ValueError('decision_must_be_boolean')
        with self._db() as db:
            quote = db.execute('SELECT * FROM data_quotes WHERE id=?', (quote_id,)).fetchone()
            if not quote:
                raise KeyError('quote_not_found')
            payload = json.loads(quote['payload'])
            if self.rehearsal_id and payload.get('rehearsal_id') != self.rehearsal_id:
                raise ValueError('rehearsal_mismatch')
            if quote['state'] == 'applied':
                if not approved:
                    raise ValueError('compensation_already_applied')
                return json.loads(quote['receipt'])
            if quote['state'] != 'pending':
                raise ValueError('quote_is_closed')
            if (time.time() if now is None else now) >= payload['expires_at']:
                raise ValueError('quote_expired')
            case = db.execute('SELECT * FROM cases WHERE id=?', (quote['case_id'],)).fetchone()
            if not approved:
                result = {'status': 'rejected', 'quote_id': quote_id, 'case_id': payload['case_id'],
                          'synthetic': True, 'receipt_id': '', 'bonus_data_gb': 0,
                          'bonus_balance_after_gb': 0,
                          'summary': 'Compensation rejected. No bonus data added. Invoice unchanged.',
                          'invoice_after_egp': case['invoice_piasters']/100}
                if payload.get('rehearsal_id'):
                    result['rehearsal_id'] = payload['rehearsal_id']
                existing = db.execute('SELECT receipt FROM data_awards WHERE case_id=?', (quote['case_id'],)).fetchone()
                if existing:
                    result['bonus_balance_after_gb'] = json.loads(existing['receipt'])['bonus_balance_after_gb']
                db.execute("UPDATE data_quotes SET state='rejected' WHERE id=?", (quote_id,))
                return result
            evidence = partner_evidence(case['service_id'])
            digest = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
            if case['version'] != payload['invoice_version'] or digest != payload['evidence_digest'] or payload['policy_version'] != POLICY:
                raise ValueError('stale_quote_reassess_required')
            if db.execute('SELECT 1 FROM data_awards WHERE case_id=?', (quote['case_id'],)).fetchone():
                raise ValueError('compensation_already_applied')
            result = {k: payload[k] for k in ('case_id', 'quote_id', 'bonus_data_gb',
                'bonus_balance_before_gb', 'bonus_balance_after_gb', 'invoice_before_egp', 'invoice_after_egp', 'policy_version')}
            result.update(status='applied', receipt_id='DATA-'+uuid.uuid4().hex[:16], synthetic=True,
                          adjustment_type='bonus_data_bundle',
                          summary='20 GB bonus data added successfully. The invoice remains unchanged at 900 EGP.',
                          human_decision_recorded=True, decision_channel='native_workflow')
            if payload.get('rehearsal_id'):
                result['rehearsal_id'] = payload['rehearsal_id']
            encoded = json.dumps(result)
            db.execute('INSERT INTO data_awards VALUES (?,?,?)', (quote['case_id'], quote_id, encoded))
            db.execute("UPDATE data_quotes SET state='applied',receipt=? WHERE id=?", (encoded, quote_id))
            db.execute('UPDATE cases SET version=version+1 WHERE id=?', (quote['case_id'],))
            return result
