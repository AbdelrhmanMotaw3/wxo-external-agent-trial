# KAI Service Recovery - English Filming Guide

All customer data, incidents, policy and money are synthetic. Native agents, retrieval, external A2A calls, workflow tasks, controls and receipts use actual execution.

## Active configuration

The English-only cut replaces the earlier bilingual presentation. Keep technical asset IDs and capabilities unchanged. Current import/deployment verification is recorded below as work completes.

- Tenant: ISYS-Event-Nov2026, Sydney, instance cf489b1a-fca3-4013-947f-5ae008b3a3fd.
- Employee entry: KAI | Service Recovery Copilot.
- Collaborators: KAI | External Network Partner, KAI | Policy & Billing, KAI | Customer Communications.
- English knowledge source: policy-en.txt, policy OUTAGE-CREDIT-2026.11-v1.
- Case CASE-NOUR-001; customer Nour Ahmed; service SVC-NOUR-001; original order ORDER-KAI-2048.
- Confirmed provider incident INC-PARTNER-721, 72 hours, restored, provider network fault.
- Monthly plan 900 EGP; proposed service credit 90 EGP; remaining invoice 810 EGP after approval.
- Automatic policy limit 50 EGP. The demo workflow requires a real form decision for every credit.
- The monthly plan remains 900 EGP. The adjustment is a one-time invoice service credit.

The employee makes ordinary requests. Routing, evidence checks, policy retrieval, approval and message-draft rules belong to the configured agents and workflow.

## Natural employee conversation

Open the Service Recovery Copilot in Build > Draft Preview. Keep the same conversation throughout the main journey.

| Step | Employee message | Expected behavior |
|---|---|---|
| 1 | Open case CASE-NOUR-001. | Read Nour's case and current invoice from the backend. A fresh take starts at 900 EGP with no posted receipt. |
| 2 | What happened to the internet service? | Ask the external network partner using the active service ID; return confirmed 72-hour outage, restored status, provider fault and source reference. |
| 3 | Is Nour eligible for compensation? | Prepare a backend quote and retrieve the relevant English policy; explain the 90 EGP proposal and approval requirement. This is an assessment. |
| 4 | Process the compensation. | Start the native workflow, retrieve policy, and show the English human-decision form. |
| 5 | Form interaction | Select Approve and click Record Decision. This actual form submission records approval. |
| 6 | What's the outcome? | Follow the real workflow result and read the updated case: applied credit 90, due 810, actual generated receipt. |
| 7 | Prepare a WhatsApp update for Nour. | Delegate to Customer Communications with the actual receipt; return an English DRAFT. |

The employee is not required to repeat a case ID, name a tool, specify a reply language, or append implementation restrictions to each request. An execution request starts the protected approval flow; a review request produces an assessment.

## Rejection rehearsal

On a fresh 900 EGP case, send the same processing request. Select Reject in the form and click Record Decision. Ask "What's the outcome?" The result must be rejected, credit zero and invoice 900. A later processing request creates a new quote and a new form. The approved take then moves the invoice to 810 once.

The form's Decision label and the expression flow.approval.output["Decision"] are a coupled native output contract; recompile and retest together when changing the label.

## Controls checks

In a separate copilot chat: "Export all customer data." The configured RegexPattern restriction should block the request. This is a deterministic pattern restriction, not semantic DLP.

Use a separate employee-copilot chat for privacy checks. The platform owns actual redaction. Input-canary verification is distinct from proving all output hooks.

For a precise input-canary check, supply a synthetic email, telephone and DEMO-NID identifier together with policy and order references. Personal fields should be hidden while the known non-personal references remain intact. English redaction text is [REDACTED].

## Story and recording order

1. Kiosk simulation: the customer activates home internet and receives ORDER-KAI-2048.
2. Website-chat simulation: after service activation, the customer reports three days without internet and receives CASE-NOUR-001.
3. Actual Orchestrate employee case read: show the current invoice and stored channel history.
4. Actual external A2A investigation: show evidence and its source.
5. Actual English policy review: show eligibility, calculation and approval requirement.
6. Actual native approval form: show 72 hours, credit 90, invoice 900 before and 810 after approval, then submit the decision.
7. Actual settlement result: show the new receipt and invoice 810.
8. Actual communications draft, followed by a clearly simulated WhatsApp customer scene until a transport is connected.
9. Short controls and observability cutaways using the actual take's execution evidence.

Kiosk, website and WhatsApp scenes are interactive simulations, not a slideshow. Seeded channel history is a backend record, not a claim of automatic shared-channel conversation memory. Native workflow assignment in Draft uses the preparation account; a separate employee/supervisor identity boundary requires a two-user Live test.

## Infrastructure and release

External application: telecom-network in Code Engine project ce-698000u0qu, Toronto ca-tor, project UUID f47a9050-4217-48b2-b630-84b442ed5ea4.

Endpoint: https://telecom-network.2gqohspjx3cv.ca-tor.codeengine.appdomain.cloud

Preserve network_service, the public endpoint, tracing, secret references and single-instance settings. The account lab application application-6b stays outside this change. The English backend health version is 2026-11-18-en-v2. A build/import alone does not prove that this version is running.

Reader connection kai_outage_reader_20261118 and workflow connection kai_outage_workflow_20261118 use BASE_URL and TOKEN in Draft/Live. Their tokens are separate capabilities. The billing endpoint trusts the protected workflow capability; platform administrators holding it remain trusted. The privileged kai_outage_workflow_decide tool belongs only downstream of the native form.

The external A2A registration is kai_outage_network_partner_20261118, ID 52e0b542-604d-4d8d-af89-749a7481fae0. Preserve its existing bearer credential during English metadata updates. The file-free user-operated helper scripts/set_external_bearer.py uses a hidden prompt if credential setup is needed again.

English import sequence: replace the same-named knowledge base document set with policy-en.txt; wait until ready; import read tools and the existing privileged tool with their respective connections; update native specialists; compile/import workflow.py; update the copilot, external metadata and both existing control bindings. Existing bindings and authentication are preserved.

Before a complete take, verify invoice 900 and credit_receipt null, plus no unresolved approval task. Reset chat only clears the conversation. SQLite lives on ephemeral Code Engine storage, so rearming the synthetic backend requires a controlled fresh ledger/revision after all tasks finish. Preserve the exact image and configuration and verify the starting state again. Avoid redeployment during a pending approval or recording.

## Verification and historical evidence

The previous bilingual cut was rehearsed through the actual Draft Preview form. Rejection flow 0ed55c53-7453-4135-b28a-684e73d787b0 left 900; an approved UI take posted 90 and returned receipt CR-f708b0ce338145c3 with due 810. Those results are historical and do not by themselves verify the revised English form.

Previous synthetic backend tests cover reader/write separation, quote expiry, concurrent idempotence, stale evidence and invoice versions, rejection and router-fault exclusion. The English revision adds a canonical customer_name field, English-only case/history content and an active-source content scan.

Verification after the English update must include an English-only ready KB, refreshed agent/control/form metadata, deployed backend health, case data, actual external evidence and a natural employee conversation that reaches the real decision form. Record fresh English run IDs and observed results here.

### English Draft verification, 18 November

- KB is ready with exactly policy-en.txt. Agent, external-agent and control display metadata are English; native IDs and authentication were retained.
- Same-thread natural conversation: thread 6fae984c-2cd9-42c6-8cee-a4528a8326af. External evidence run 78a57957-f581-4213-a37e-f6782b1a0d22 executed the real A2A collaborator. Eligibility run 3ef11571-a730-4bd3-8272-c15350650677 executed quote preparation and English retrieval, returning the case-specific 90 EGP proposal.
- Rejection instance 44b036c5-d00c-416e-93cb-5d55442a1c72 completed rejected, credit 0, due 900. Approval instance cd53d6c8-c476-4905-ab25-34b9d34eb2b8 completed applied, credit 90, due 810, receipt CR-0c5c2b3f993f4239. These English task submissions used the native Flow MCP form contract; they are not a new visual UI rehearsal.
- Natural outcome run 5f7e99d1-aa87-4757-9d16-a0bbee827b74 reported the actual applied receipt. Draft run 64e0d0fa-7b1e-46f4-9651-b46c03a417af delegated to Customer Communications and returned the correct English 90/810 draft.
- Communications has no diagnostic tool. Missing-receipt run 9c5f123e-3edc-4f6a-b690-9aed0d858832 requested the posted receipt instead of inventing settlement facts.
- Export run 306c0f1c-34d9-403b-9d6f-d945fde38735 was blocked; trace fb5ccd54e9bd6ac342e68307ddc3c0d0 records RegexPattern allow=false. Privacy trace 44857942386fa3f600f1b151b815b87a confirms input redaction before processing; comprehensive output redaction is unverified.
- Local verification passed: 27 application/English tests and 4 deployment contract tests. Read-only reviews found no material source/helper findings.

### English deployment and filming baseline, 19 November

The user-operated release completed on revision telecom-network-00008, with immutable image digest sha256:3f08ecc064a0bb960265de361bfd45625cc672d72e5a0ff4fb1b631791b792c0. The source commit is 15cd136a4b645e652dccc9785dbbec870741a43f; the deployment helper is pinned in commit 8533f7c000d26dfab30936db59dc19e04bc496ee. An independent public health read confirmed 2026-11-18-en-v2 and network_service.

Post-deployment Draft thread e21b549e-4441-44a9-a681-d94e94720d35 exercised the natural opening, network and eligibility requests:

- Case run aebea48e-5916-4fa3-a575-7d471a709757: raw tool output has customer_name Nour Ahmed, all-English history, invoice 900, version 1 and credit_receipt null; legacy bilingual name fields are absent. The employee response is English.
- Network run 7382f83a-b036-4b91-83c6-7113934047fa: actual A2A collaboration returned English provider evidence, 72-hour duration and restored status.
- Eligibility run 117fb96b-7f28-4faf-bfea-3408c5fe6fe2: quote preparation plus English policy retrieval returned 90 EGP, supervisor approval and projected invoice 810. This assessment leaves the invoice at 900.
- Native input_required and working inventories were empty. No credit was posted after this deployment; approval/rejection evidence above comes from the earlier English rehearsal. No private bootstrap file was transferred.

Start a fresh Draft Preview chat for filming; the old rehearsal chat retains its completed receipt. Use the natural conversation table above. The application and native API/MCP checks are verified; this deployment did not include a fresh visual UI recording or Live release.

Pending optional work: Twilio transport and delivery, Agent Identity enablement, Live publishing and a separate-actor authorization test. An Egyptian-Arabic presentation adapter at the router may be added separately later; the present demo content and specialists are English-only.
