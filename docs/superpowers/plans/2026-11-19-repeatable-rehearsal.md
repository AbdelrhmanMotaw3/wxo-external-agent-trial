# Repeatable conversation rehearsals and complete WhatsApp output

## Accepted behavior

Every new Orchestrate conversation gets independent synthetic cases starting at 900 EGP with no posted receipt. Turns in the same conversation share state; rejecting keeps 900, approving posts 90 once and leaves 810. Old conversations and concurrent pending approvals must not reset or affect a new conversation. Case/customer/service identifiers remain unchanged in visible copy. Native human approval and the separate writer capability remain required.

The supplied screenshot proves that the prior WhatsApp widget emitted only its title in the native UI. Every preview and dispatch must therefore carry a complete native Markdown result as its primary output, including the canonical message, masked recipient, status and reference. A send request without an earlier preview should prepare and dispatch the current canonical receipt-grounded message in the same action. A draft alone never records Sent. No provider API is called.

## Architecture

Use the platform-populated wxo_thread_id through an injected AgentRun context, not a model-generated session ID or a run ID that changes every turn. Verify context propagation before integration. Read/quote tools pass the conversation ID in an authenticated X-KAI-Rehearsal-ID header. The backend namespaces synthetic case/credit storage by that ID. Stored quotes bind their namespace, so the existing writer can resolve the correct case by quote_id even when a policy-agent child changes workflow context. Legacy unscoped requests remain compatible.

## Work and checks

1. Probe context on the existing non-financial diagnostic Draft agent; restore the temporary changes after testing stable IDs across turns, new IDs across chats, and workflow preparation context.
2. Test isolated backend stores and API: fresh A/B both 900, A approval leaves B at 900, duplicate A blocked, rejection does not settle, cross-session quote association cannot be confused, legacy behavior preserved and malformed namespace rejected.
3. Add injected context to reader/notification tools. Refuse missing context or a backend that does not acknowledge the requested namespace. Preserve the approved workflow form, mapping and writer restrictions.
4. Replace title-only WhatsApp output with complete readable native content. Preserve exact prepared text when a draft ID is supplied; permit explicit direct send to prepare the current receipt-grounded message when no draft was shown. Always mask the phone as +201********* and record the scenario/provider boundary in structured metadata.
5. Prepare a pinned, credential-preserving Code Engine release helper that updates only the existing network application's image. Keep Cloud Shell user-operated. Deploy the backward-compatible backend before activating the new context-aware Draft tools.
6. Verify independent actual conversations and the real human workflow path. Do not infer UI rendering from API success; use actual visible native output or a user rehearsal for the final visual check. Do not publish the full demo to Live without authorization.
