# KAI Service Recovery - English Filming Guide

**Current verified scenario:** one-time **20 GB bonus data**, with the invoice unchanged at **900 EGP**. See [the data-compensation rehearsal guide](DATA_REHEARSAL.md) for the active contract and filming steps. V4 is deployed and activated in Draft. The user confirmed successful native UI approval and conversation continuation; the corresponding workflow completed without errors. The financial-credit scenes below are historical evidence, not the current filming script.

All customer data, incidents, policy and money are synthetic. Native agents, retrieval, external A2A calls, workflow tasks, controls and receipts use actual execution.

## Active configuration

The English-only cut replaces the earlier bilingual presentation. Preserve the existing agent IDs, connection IDs and capabilities. The active workflow was re-registered under a new technical identity after the UI investigation; use the verified identity below.

- Tenant: ISYS-Event-Nov2026, Sydney, instance cf489b1a-fca3-4013-947f-5ae008b3a3fd.
- Employee entry: KAI | Service Recovery Copilot.
- Active Draft workflow: kai_outage_credit_workflow_20261119, ID fa7ab96e-be92-48f8-90e6-d4b91141dc0d, display name Outage Credit Approval. The previous 20261118 workflow remains available for rollback and is no longer bound to the Draft copilot.
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
| 7 | Prepare a WhatsApp update for Nour. | Review the actual receipt with Customer Communications, then prepare the canonical English draft and native preview card. |
| 8 | Send it to Nour on WhatsApp. | Run the scenario transport for Nour's synthetic saved contact and return a native WhatsApp sent card. No provider API is called. |

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

### Subsequent native UI investigation, 19 November

Intermittent Draft form stalls were reported after the card displayed Submitted. A stored user form submission can exist while the native human task still reports input_required. Recovery of the original recorded rejection completed the human task, but its downstream task then failed with Failed to refresh token. This is distinct from proving a form-mapping defect.

The unchanged full workflow subsequently completed two real Draft UI rejection tests: 84cd7196-c410-491f-af0f-0f0f206a65ae and e5ad9412-a4b3-47d7-a170-71123bba210a. Both returned rejected, credit 0 and invoice 900. A full Draft UI approval also completed as instance 3f022bd6-4c22-4b41-b752-592a88afc227, quote Q-b2114ba2db9249b3, receipt CR-ad061e44011b4d23, applied credit 90 and invoice 810. All prepare, policy, human-decision and recording steps completed without an error.

That historical UI approval left the case at 810. A later user-operated fresh-ledger reset restored 900 before the final test below. Repeating a credit request after an applied credit should be rejected by the backend's duplicate-credit guard.

Only the separate non-financial KAI | Form Diagnostic agent was explicitly authorized and published to Live. Its agent ID is 90648bed-84e2-4819-a7fc-59e6ad873c46 and form-only flow ID is a3f402e4-c258-4248-99df-edbc6e302844. The user reported successful diagnostic tests in both Live and Draft. The original demo copilot has not been published to Live as part of this investigation.

The user subsequently completed the diagnostic form with the cloned PII control, a policy-agent handoff, a post-form Python tool, their combined sequence, and the combined sequence with both cloned PII and Regex controls. These tests did not reproduce the failure. Original demo control bindings remain unchanged. Individual controls and the policy/form/Python sequence were not demonstrated to cause the stalls.

### Verified clean-registration workaround, 19 November

The complete workflow was re-registered as kai_outage_credit_workflow_20261119 (fa7ab96e-be92-48f8-90e6-d4b91141dc0d) and the existing Draft copilot was rebound to it. Source and compiled definitions are identical to the previous version after normalizing the technical name, including schemas, graph, user assignment and the Decision output mapping. Human approval, the downstream-only settlement tool, separate reader/writer connections and the original controls are preserved. No backend code or image change was required for this workaround. The old registration is retained for rollback.

After the user reset the synthetic ledger, case-read run 114d0abb-6eb7-4543-b36d-7be6c3703a0e verified invoice 900 and no receipt. The user then tested the original employee scenario in the browser that had exhibited stalls and reported that both Reject and Approve returned normally. Independent native execution inspection confirmed both runs used the new workflow model:

| Decision | Workflow instance | Result | Invoice due | Receipt |
|---|---|---|---|---|
| Reject | 652dd276-4253-4bf2-bf09-cd19f3c5080b | rejected; credit 0 | 900 EGP | none |
| Approve | 83ce3829-32b2-438a-8070-7c742eb36fc6 | applied; credit 90 | 810 EGP | CR-df4d0899ca1b4474 |

Both human tasks and all downstream tasks completed without an error. Approval quote: Q-4ffd42d8437a4c26. Trace IDs: rejection 589832cd2e01dc9e7dbc846eaee805f0; approval c0c4dd24f84748e83056d60a71f1b716. These are observed UI and native-runtime results for a clean registration; they do not establish a permanent root-cause fix in the platform.

The latest verified case is now at 810 with that receipt. Continue with "What's the outcome?" and "Prepare a WhatsApp update for Nour." for the remaining scenes. Start a fresh 900-EGP take only after a controlled ledger reset and a new case read. The two new test workflows are terminal; older stalled tasks reference quotes absent from the fresh ledger and must not be replayed as new approvals. The full demo remains Draft; only the diagnostic agent was published to Live.

Final independent case-read run e404bd78-a153-49ce-94ec-2c4e32b6dc0a executed kai_outage_get_case and reported invoice 810, applied credit 90 and the same receipt. Local verification passed 10 business/English tests and 3 API authorization tests, plus source/compiled equivalence, agent tool-boundary checks and git diff --check. The API tests required execution outside the sandbox because their local TestClient initialization stalled inside it; tracing was disabled for these local tests only.

### WhatsApp scenario transport, 19 November

Draft copilot tools kai_outage_whatsapp_preview (71163c7f-e205-44aa-88b3-af3a61d9ee55) and kai_outage_whatsapp_send (6a70daaf-5e10-4e25-a0cd-a1dec593f8a2) use only the existing reader connection. They are placed on the entry agent so native card metadata does not depend on a collaborator hop. Customer Communications remains the receipt-review specialist. The existing approval workflow, privileged billing-tool boundary and original control bindings are preserved. No Code Engine rebuild, credential change or Live publication was performed.

Preview and dispatch independently read the posted receipt. A changed receipt invalidates the old draft. The canonical draft is unchanged by dispatch. The simulated send emits an internal KAI-WA reference and a Sent card; structured metadata explicitly records simulated=true, provider_dispatch_performed=false, provider_message_id=null and delivery_status=not_attempted. There is no provider outbox or delivery persistence. A stable reference on repeated calls is not evidence of an actual provider transaction.

Eight local contract tests pass, covering missing receipt, stale draft / invoice, invalid or redacted recipient, stable message reference, unchanged body, fresh case read and native-card metadata. Initial API preview run 09e0c118-2eab-4e48-8a54-757a729bade5 returned WhatsApp message ready. Follow-up d1397271-43b4-4518-a3a0-0e3dc24278df returned WhatsApp sent through the new dispatch tool in thread 8b169eb0-0ba0-49e6-ae65-8e934311110e. These runs verify tool execution; visual card rendering remains pending the user's browser test because the embedded-browser session required sign-in. Use the rehearsal instructions below and report whether a card or text alone appears.

For the notification-only rehearsal, open a fresh Draft Preview and send: Open case CASE-NOUR-001. Then: Prepare a WhatsApp update for Nour. Then: Send it to Nour on WhatsApp. The current posted receipt supports this test without resetting the invoice. For the full compensation journey, first restore the 900/no-receipt baseline through the user-operated ledger reset, then complete a new human approval and prepare a fresh WhatsApp draft. Redacted numeric recipients are never guessed; the saved-contact wording avoids ambiguous destination selection under the existing PII control.

### Settled-case handling and masked recipient, 19 November

A reported 409 was a duplicate-credit guard on the existing applied receipt CR-df4d0899ca1b4474, not a failed fresh approval. An independent case read confirmed invoice 810 and the same receipt. Draft copilot instructions now check existing settlement before preparing a quote or starting another workflow. Fresh-chat run ceb50fad-8d0d-4aac-b8c1-cffd0687cf8c called only kai_outage_get_case, returned the actual applied 90 / remaining 810, and started no new workflow. A new chat does not reset the ledger. A fresh approved take requires a separately verified 900/no-receipt baseline.

WhatsApp recipient display now preserves only the international prefix and first national digit, masking every remaining digit. Nour's synthetic saved contact displays +201*********. The full number and last-four-digit suffix are absent from the outgoing card/result. Fresh preview run 40979135-cd5e-441d-b7c1-3fb1cee8676a and send run 7ce4d6a8-0b7a-4bb5-ada9-9cef6775bc03 verified recipient +201********* in the actual structured tool payload. The scenario still performs no provider dispatch. Nine notification tests plus ten business/English tests passed.

Timestamp privacy investigation: controlled echo run 47948435-259b-4a1b-9fed-c8401eaca1f5 reproduced redaction of the four known synthetic timestamps. Adding exact date/timestamp exceptions to the diagnostic-only PII clone preserved all four timestamps in run 24978412-603e-4225-9c33-9001afedb665 while email, telephone and the synthetic identifier remained redacted. Diagnostic instructions and clone configuration were restored after the comparison.

The user subsequently explicitly approved applying those exact exceptions to the existing shared business control across the three bound agents in Draft and Live. The config-only patch was applied to binding 02d5ee31-368f-4732-b2bf-4fafec14242d, now version 5, and independently read back. It adds only the four anchored event date/timestamp patterns in pii.yaml. Existing email/phone detection, custom identifier pattern, redaction strategy/text, logging settings, hooks, priority, activation state and agent/tool/model mappings were all unchanged. No agent release was published and no billing data was reset. The earlier automatic-review block is resolved by that explicit approval. Verification metadata is saved locally under runtime/approved-incident-date-control-verified.json.

Post-change copilot run 7a743ec1-6f3b-45bb-80f3-de0ee3f60fd7 returned the correct start and restoration dates, UTC times and 72-hour duration without redaction in the API answer. It reused the active conversation context and made no new external call; this is not a new visual browser check. Refresh Draft Preview before the next user-side UI verification.

### Conversation-isolated rehearsals: pre-rollout preparation record

This section supersedes the shared-ledger/reset instructions above **after** the v3 backend and the context-aware Draft tools are activated together. A new conversation then starts CASE-NOUR-001 at 900 EGP with no receipt; subsequent turns retain that conversation's approval, rejection and invoice. Opening a new chat no longer requires a ledger reset. Returning to an existing chat retains its settlement while its ledger is available.

The scope is the platform-injected `wxo_thread_id`, not a model-generated argument or the per-message run ID. Native diagnostic runs e49f256a-aeb9-41f1-8f9c-72ad4653817a and 4c74d65b-9742-47bb-a7f8-ec299d97036d returned the same chat ID; a new chat returned a different ID. Native flow 65296f54-2ef2-477e-8a27-936d79b411e8 completed and its tool received the original chat ID. Temporary diagnostic Draft instructions, tools and context whitelist were restored and independently read back afterward.

Reader and quote tools pass `X-KAI-Rehearsal-ID` through the existing reader connection. They reject missing context or a backend that fails to acknowledge the scope. Stored quotes bind the private ledger namespace; the existing workflow writer resolves the matching case from its stored quote. The native form, policy review, separate writer credential, duplicate-credit protection and workflow-only writer attachment are preserved. This is synthetic recording isolation, not an end-user authorization mechanism.

The user's screenshot demonstrated that the earlier widget rendered only its title. The new WhatsApp tools return an official ToolResult with complete primary Markdown: status, case, receipt, message body and, for Send, the masked recipient and internal message reference. Explicit `Send to WhatsApp` can compose the current canonical message inline. A supplied draft must still match the current receipt. Repeated sends for that receipt/contact use a stable internal reference; another receipt gets a different reference. No provider transport or delivery is attempted.

Fresh local verification: 23 backend/API/English tests, 17 tool/notification tests and 8 release-helper tests passed. An initial helper-test invocation used Python without the Code Engine SDK; rerunning with the existing application virtual environment passed all eight helper checks. Native human approval with the new scoped backend and actual UI rendering remain **unverified pending rollout**.

Release order: run `scripts/cloudshell_rehearsal_release.py --source <full-reviewed-commit>` in authenticated IBM Cloud Shell; verify public health version `2026-11-19-en-v3` and `rehearsal_sessions=true`; then enable the Copilot's `wxo_thread_id` context and import the new reader/WhatsApp tools into Draft. The helper updates only the existing telecom-network image using an exact source/digest and ETag guard. It neither reads nor modifies secret contents, connection values, runtime environment or scaling. The historical v2 helper must not be used for this release. The full demo remains Draft; Live publication requires its own authorization.

After activation, test two actual new chats: approve in A (810), read B (900), reject in B (900), then approve in B (810 with a distinct receipt). Confirm a repeated credit in A stays 810, and inspect both prepare/send output in the native UI. Code Engine local disk remains ephemeral; changing/replacing its instance can discard all conversation ledgers. Avoid deployments during a pending approval or a recording take.

### V3 activated and native runtime verified, 19 November

The user completed the Cloud Shell release of c5266aaa8c4b18703b11634ad1c5ce413e74238f. Independent public health verification returned network_service, 2026-11-19-en-v3 and rehearsal_sessions=true. The reviewed reader and notification tools were then activated on the existing Draft copilot. All four tool UUIDs, collaborator attachments and approval workflow UUID were preserved. The privileged writer remains absent from the chat agent. No credentials, business controls or Live agent releases were changed.

Actual conversation A, 94e51762-cf2a-45a4-8b9a-8961fe4d432a, opened at 900 with no receipt. Policy retrieval proposed 90. Native approval 0d719eab-c61a-4f80-a64a-6ae0d85aa17a completed with receipt CR-a2844a592c074d81 and invoice 810. A repeat compensation request reported the existing credit and started no further workflow.

Actual conversation B, d4646ee5-6ada-4e4d-ab73-9044227eb1d8, still read 900/no receipt after A settled; the tool payload acknowledged B's own thread ID. Native rejection 3d485e44-9d4b-4492-a9ba-6695934b6249 completed at 900. A subsequent ordinary retry completed native approval ecb68f1a-387b-4a9c-8aba-e4af5a7b12eb, leaving 810 with the distinct receipt CR-c0dea9cfd9e94a6a. Every recorded preparation, policy, decision and settlement task completed without an error. These form submissions exercised the native MCP contract using the preparation account; they were not mouse-driven UI tests or a separate-actor authorization test.

A third chat, 96804e5b-2de1-4b6d-b18c-21caefa92127, created after both approvals independently returned 900/no receipt. No ledger reset was performed. Its real A2A collaborator call returned the 72-hour restored outage, the expected incident reference and unredacted event timestamps. Case IDs and customer-facing details stayed unchanged.

Direct `Send to WhatsApp` run b657ab24-2053-4388-88f9-ed0cf62a8514 invoked the send tool and returned complete native Markdown, not just a title. Preparation run c7354362-8821-477f-9dbe-922a83d208f2 returned the full canonical message and visible draft reference. Follow-up send run 00172783-5db7-4652-a633-3793dbd35875 returned the identical message, recipient +201********* and stable reference KAI-WA-15705a15c1e1d173. The full synthetic phone number was absent. Native tool events retained content and _meta, but omitted structuredContent; the draft reference was therefore added to primary preview content and verified with a regression check. The observed metadata explicitly records scenario transport and provider_dispatch_performed=false. There is no real provider dispatch or delivery receipt.

The 17 affected tool tests passed after the visible draft-reference adjustment. Independent integrated assertions verified the three terminal workflows, distinct receipts, untouched B before its approval, fresh C baseline, identical preview/send bodies, masked recipient and real A2A evidence. Local proof is runtime/rehearsal-verified-results.json; ignored runtime files are not published. Visual rendering in the user's native UI remains the final rehearsal check.

For each recording take, refresh Draft Preview and choose **New chat** on KAI | Service Recovery Copilot:

| Step | Employee message or action | Expected result |
|---|---|---|
| 1 | Open case CASE-NOUR-001. | Nour Ahmed; invoice 900; no credit receipt |
| 2 | What happened to the internet service? | External Network Partner; restored 72-hour outage |
| 3 | Is Nour eligible for compensation? | Policy citations; proposed 90 credit; approval required |
| 4 | Process the compensation. | Native Review Service Credit form |
| 5 | Approve, then Record Decision | Applied 90; remaining 810; posted receipt |
| 6 | Prepare a WhatsApp update for Nour. | Complete English draft and draft reference |
| 7 | Send it to Nour on WhatsApp. | Complete Sent result; masked contact; message reference |

For the rejection scene, choose Reject at step 5; the invoice remains 900. Then send Process the compensation again. and approve the new form. Start another take with New chat rather than replaying a completed conversation. Direct Send to WhatsApp after approval is also supported without a preview step.

### Case-ID capitalization correction, 19 November

The user's `open case CASE-Nour-001` reached the backend unchanged and returned 404 because the stored identifier is CASE-NOUR-001. Draft case reads, quote preparation and notification reads now uppercase the supplied case ID and trim surrounding whitespace before lookup. Public records retain their canonical identifiers; unknown case IDs remain unknown. No prompt workaround, ledger reset, backend rollout, control change or Live publication was required.

Three regression checks reproduced the missing normalization before the fix. Afterward, all 20 ADK tool tests and all 37 offline application tests passed using their respective existing dependency environments. The application checks emitted the pre-existing create_react_agent deprecation warning. Native Draft run 6ee3ac6c-c04f-4272-bc62-ac18319222ce, thread 895f4e8f-3547-4adc-baec-0730fc7ab4d3, then successfully executed the user's exact original message and returned canonical CASE-NOUR-001, Nour Ahmed, invoice 900 and no receipt. All four existing tool registrations were updated in place.

### Native UI stall recurrence: context restoration under verification

The user reported another stall in thread 65965e03-1821-460d-95c9-d99290fe7b81. Workflow bb411242-f09c-4e2c-a724-7d3a94ce2ad0 had completed preparation and policy review but remained input_required. The native UI had already stored the exact Approve submission for quote Q-e06a845e68b6424a at 14:46:40 UTC. Its form metadata recorded synced=false. Therefore selecting/submitting the form was not missing, and billing had not yet started at that snapshot.

The stalled workflow's input contained only wxo_thread_id plus engine-generated routing fields. The earlier successful user UI runs contained all five standard system context values. Conversation scoping had narrowed the Copilot's context allowlist to the thread ID. Draft access now preserves wxo_thread_id, wxo_run_id, wxo_tenant_id, wxo_email_id and wxo_user_name. Values remain platform-populated; no system value is manufactured or overwritten. Tool IDs, workflow graph, approval assignment, controls, credentials and Live releases are unchanged. This restores an observed difference from the working baseline; it is a candidate correction, not yet proof of the original stall's root cause.

The original stored approval was replayed through the native MCP form contract only after checking matching message/parent, case, quote, conversation, boolean decision and quote expiry. No new decision was selected and the billing endpoint was not called directly. The human task completed, but the downstream tool task failed with TaskRunError: Failed to refresh token. The old instance is therefore failed, not successfully compensated; no receipt was returned. The attempt to read the same locked chat through Runs was rejected with HTTP 400. Do not replay this terminal workflow as a new approval.

A regression check now requires the standard system context alongside rehearsal scoping. All 21 context/tool checks passed. The preceding 37 offline application checks remain the latest application verification because no application code changed. Fresh native UI approval/rejection is still required; prior successful MCP submissions do not prove native UI submit reliability. The user has been asked to refresh Draft Preview, start a new chat and retest the original employee flow with the restored context. No further backend deployment or ledger reset is needed for this configuration change.

The user retested and the stall recurred as workflow 1011b42c-30fd-4e98-a46b-ca887c6de0e4 in thread fc0057d7-13aa-4f13-84dd-2b142c4d351b. This instance demonstrably received all five restored context values; context restoration therefore did **not** resolve the UI-submit failure. At the inspected snapshot, preparation and policy were completed, the workflow remained input_required, and a single stored Approve submission for Q-167e3355eb4948a6 was present with synced=false. The flow-start and policy-associated runs were completed without a last_error; that is not evidence that form synchronization succeeded. The newer pending approval was not replayed or settled during this inspection.

Direct browser diagnosis is currently blocked: cua_repl returned `Local browser use is disabled in Work settings`. The user has been asked to enable that capability so the actual native submit/console path can be inspected. Do not replace the native human task, weaken controls, repeatedly re-register the same flow or claim the issue fixed from MCP-only success. Local context changes and the preservation test remain uncommitted pending resolution; no new backend deployment or Live release was performed.

### User-requested repeat of the earlier clean-registration workaround

The user explicitly requested reviewing and repeating the action that had previously succeeded. Historical state and saved native UI results confirmed that action was a fresh equivalent workflow registration followed by rebinding the Draft copilot. The current source and compiled graph were independently identical to that successful registration. An additional registration was therefore created specifically under this renewed request: kai_outage_credit_workflow_20261119_r2, UUID 07c9af63-3a59-44a5-8c24-c6cdb5dc0a70. Its compiled definition was verified exactly equal to the preceding definition after normalizing only the technical name, including all schemas, approval mapping, assignment and execution graph.

The existing Draft copilot now references the r2 workflow UUID/name. All other tool IDs, collaborators, context access, native approval and workflow-only writer restrictions were independently read back unchanged. The previous workflow remains available for rollback, and old pending attempts remain associated with it. Backend data isolation, application image, connections, secrets, business controls and Live releases were not changed. Unlike the original workaround, no ledger reset is needed because a new conversation supplies a fresh synthetic namespace.

This is an applied workaround awaiting a fresh user UI test, not a demonstrated fix for the platform's submit synchronization or token-refresh failure. Refresh the agent page and start New chat before Open case CASE-NOUR-001. and Process the compensation.; an old form cannot exercise the new registration. Candidate source/compiled artifacts and rollback/binding evidence are retained in ignored runtime files. Do not promote the canonical workflow name or claim UI success until native UI submission is confirmed.
