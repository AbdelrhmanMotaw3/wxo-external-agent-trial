# 20 GB outage compensation rehearsal

## Current contract

Nour Ahmed, CASE-NOUR-001, SVC-NOUR-001, ORDER-KAI-2048. The partner confirms a restored 72-hour provider outage. The fictional event policy proposes one fixed 20 GB bonus data bundle. Native approval is required. Approve grants the bundle once and returns a DATA receipt; Reject grants nothing. The invoice and recurring plan remain 900 EGP. Compensation data balance is 0 GB before approval and 20 GB afterward; this is separate from the customer's total plan allowance. No validity period has been specified, so none is invented.

Each new conversation has its own rehearsal. Earlier financial records are isolated under their old storage keys and never reused or reset. The new data ledger uses its own namespace and quote/award tables. Pending old financial workflows must not be replayed after this migration.

## Prepared assets and activation order

- Backend release: 2026-11-19-data-v4. Health must report rehearsal_sessions=true, compensation_type=bonus_data and compensation_gb=20.
- New KB: kai_outage_data_policy_20261119, ID d83ed089-66e7-41c9-b0a2-5c1e5d8c5324. One English policy document, indexed ready. Policy ID OUTAGE-DATA-2026.11-v1.
- New execution flow: kai_outage_data_workflow_20261119, ID 87f9897e-1cbb-40f7-97ba-3da5232c315e. Display: Outage Data Compensation Approval.
- Existing employee, policy and communications agent IDs, connection IDs and external agent remain unchanged.

Deploy the reviewed backend with scripts/cloudshell_rehearsal_release.py --source FULL_COMMIT in authenticated user-operated IBM Cloud Shell. The helper patches only the existing telecom-network image and preserves environment, scaling and secrets. It verifies the source commit, immutable image digest and health contract. The application-6b deployment is outside this release.

After health verification, run scripts/activate_data_draft.py in the local authenticated ISYS-Event-Nov2026 CLI environment. It updates the reader, notification and workflow-only provisioning tools, attaches the ready data KB to the existing policy specialist, and rebinds the Copilot to the new flow. The privileged tool remains absent from the chat agent. No business control change or full-demo Live publication is included.

## Workflow continuation investigation

The original UI stalled after storing an Approve form submission, while the native task remained input_required and the form metadata recorded synced=false. Re-registering the identical flow and restoring full standard context did not establish a durable fix. An earlier recorded submission replay advanced the human task but then failed with Failed to refresh token. API/MCP-only success is insufficient evidence of UI submit reliability.

The new execution flow keeps preparation, native human approval and provisioning, with an explicit final summary and structured result. Policy retrieval occurs through the existing Policy Agent before the Copilot starts execution; the backend independently revalidates eligibility, evidence, policy and case version. Removing the inline agent handoff from the pending approval flow is a bounded repair candidate, not a proven platform root cause. The reviewer, real form, stored-quote checks, separate writer capability and duplicate-award guard remain.

Acceptance requires visible native UI results after both Reject and Approve, followed by a successful ordinary chat message and WhatsApp preview/send. The full conversation must resume without manual MCP recovery. Browser control was last unavailable because Work returned Local browser use is disabled in Work settings. As of preparation, native UI verification is still pending; do not claim this issue fixed.

## Employee rehearsal

Refresh Draft Preview and start New chat. Send:

1. Open case CASE-NOUR-001.
2. What happened to the internet service?
3. Is Nour eligible for compensation?
4. Process the compensation.
5. In Review Bonus Data Compensation, select Approve and Record Decision.
6. What is the outcome?
7. Prepare a WhatsApp update for Nour.
8. Send it to Nour on WhatsApp.

Expected approval output: applied, 20 GB awarded, compensation data balance 20 GB, unchanged invoice 900 EGP, posted DATA receipt and a clear summary. Expected rejection output: rejected, 0 GB awarded, unchanged invoice 900 EGP. After rejection, Process the compensation again. should produce a new form. A repeated approval in the same chat must not add another bundle. A new chat must start at 0 GB and 900 EGP.

The WhatsApp result contains the full receipt-grounded English message, masked recipient +201*********, status and internal KAI-WA reference. It is scenario transport with no provider dispatch or delivery receipt. The recurring subscription and invoice are not discounted. All visible customer and business content remains English.
