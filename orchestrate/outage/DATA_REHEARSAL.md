# 20 GB outage compensation rehearsal

## Current contract

Nour Ahmed, CASE-NOUR-001, SVC-NOUR-001, ORDER-KAI-2048. The partner confirms a restored 72-hour provider outage. The fictional event policy proposes one fixed 20 GB bonus data bundle. Native approval is required. Approve grants the bundle once and returns a DATA receipt; Reject grants nothing. The invoice and recurring plan remain 900 EGP. Compensation data balance is 0 GB before approval and 20 GB afterward; this is separate from the customer's total plan allowance. No validity period has been specified, so none is invented.

Each new conversation has its own rehearsal. Earlier financial records are isolated under their old storage keys and never reused or reset. The new data ledger uses its own namespace and quote/award tables. Pending old financial workflows must not be replayed after this migration.

## Active Draft assets

- Backend release: 2026-11-19-data-v4. Health must report rehearsal_sessions=true, compensation_type=bonus_data and compensation_gb=20.
- New KB: kai_outage_data_policy_20261119, ID d83ed089-66e7-41c9-b0a2-5c1e5d8c5324. One English policy document, indexed ready. Policy ID OUTAGE-DATA-2026.11-v1.
- New execution flow: kai_outage_data_workflow_20261119, ID 87f9897e-1cbb-40f7-97ba-3da5232c315e. Display: Outage Data Compensation Approval.
- Existing employee, policy and communications agent IDs, connection IDs and external agent remain unchanged.

Deploy the reviewed backend with scripts/cloudshell_rehearsal_release.py --source FULL_COMMIT in authenticated user-operated IBM Cloud Shell. The helper patches only the existing telecom-network image and preserves environment, scaling and secrets. It verifies the source commit, immutable image digest and health contract. The application-6b deployment is outside this release.

After health verification, run scripts/activate_data_draft.py in the local authenticated ISYS-Event-Nov2026 CLI environment. It updates the reader, notification and workflow-only provisioning tools, attaches the ready data KB to the existing policy specialist, and rebinds the Copilot to the new flow. The privileged tool remains absent from the chat agent. No business control change or full-demo Live publication is included.

## Workflow continuation investigation

The original UI stalled after storing an Approve form submission, while the native task remained input_required and the form metadata recorded synced=false. Re-registering the identical flow and restoring full standard context did not establish a durable fix. An earlier recorded submission replay advanced the human task but then failed with Failed to refresh token. API/MCP-only success is insufficient evidence of UI submit reliability.

The new execution flow keeps preparation, native human approval and provisioning, with an explicit final summary and structured result. The eligibility question is the Policy Agent/KB scene. A processing request directly starts the execution flow; authoritative backend checks revalidate eligibility, evidence, policy and case version. Removing the inline agent handoff from the pending approval flow is the applied structural change; it does not establish a general platform root cause. The reviewer, real form, stored-quote checks, separate writer capability and duplicate-award guard remain.

The user tested the new native UI approval and subsequent conversation and reported that everything worked. Independent inspection verified completed workflow ecb6a354-654e-4ba1-9b46-14cd928227c9, model 87f9897e-1cbb-40f7-97ba-3da5232c315e, in thread cf9e2b3f-b51b-4068-a394-bf8fbdd40cd3. Its native human decision was true; preparation, provisioning and flow end all completed without errors. Output: 20 GB awarded, compensation balance 20 GB, invoice 900 EGP, receipt DATA-215c144d7a1b40bc and an explicit success summary. This user UI attempt was not recovered or submitted through the agent's MCP test helper.

Separate agent-operated MCP tests verified Reject (instance 322fc3f1-0a38-46d2-9ab6-fded14b5a522: 0 GB, invoice 900), ordinary conversation after rejection, retry, and Approve (instance 7c56c933-ca4d-4cec-8d6e-2ea9a389fac5: 20 GB, invoice 900, receipt DATA-ef471a8998ee4f63). These are distinct from the user UI approval evidence; a fresh native UI Reject is not claimed. Another chat read 0 GB/no receipt/900 after the first chat settled. Repeating compensation in the settled chat reported the same receipt without starting another workflow.

Two prompt-routing issues found during rehearsal were corrected in Draft: processing intent now starts the execution flow rather than stopping at another policy explanation, and WhatsApp preparation directly calls the canonical preview tool rather than stopping at a communications handoff asking for already-available receipt fields. Customer Communications remains available for a separate wording review. Actual preview tool run a257fb79-7953-4d01-8700-4d05179ec986 returned the complete 20 GB/900 EGP message and a visible draft reference. Sent run c69c38ae-9a56-4a3e-b12c-d87a7fb93daa returned the full message, masked recipient and KAI-WA-22fd19e705e42e97. A preview POST initially timed out at the client; stored native events independently confirmed a later actual preview tool result. A subsequent read-only recap reused that visible draft. Scenario metadata confirms no provider dispatch.

Fresh local checks: 49 backend/release tests plus 22 ADK tool/context/workflow tests passed. Live publication and business control changes were not performed. The user-operated backend source is 6852c9d66a4ee403388cfa49663735fa630e0e73; subsequent changes are Draft instructions and documentation, so no further Code Engine deployment is needed for this baseline. Browser control remained unavailable in Work settings, so UI success is based on the user's report plus the corresponding independent native execution record, not a screenshot captured by this agent. The CLI expired during an optional final thread-message read after the successful workflow record had already been verified; no additional credential refresh was needed to establish that result.

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
