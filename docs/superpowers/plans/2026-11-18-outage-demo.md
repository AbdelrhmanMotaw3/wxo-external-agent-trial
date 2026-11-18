# Internet outage compensation — implementation plan

Goal: Film a real bilingual Orchestrate investigation and controlled invoice adjustment using synthetic telecom records.
Architecture: native employee copilot delegates policy work to a native KB specialist and network investigation to the existing external LangGraph/A2A service. Native workflow owns human approval and privileged billing operations. Communications prepares an auditable message; sending requires a configured transport and authorized destination.
Tech stack: Python 3.12, FastAPI, LangGraph, watsonx Orchestrate ADK 2.18.2, bilingual policy documents, native workflow and native PII control.
Spec: this document records the user-approved outage scenario and latest bilingual requirement.

## Global constraints
- Separate clone on codex/telco-outage-demo; preserve existing profiles/routes and all previous demos. Never modify KAI-Production.
- Fictional demo policy OUTAGE-CREDIT-2026.11 v1: 72 confirmed hours, monthly base 900 EGP, 30-day calculation, credit 90 EGP, automatic cap 50 EGP, unpaid invoice 900 -> 810. Base subscription stays 900. Service credit, not cash refund.
- Never accept model-written approval claims or arbitrary amounts as authority. Only a completed human workflow step reaches privileged billing tools. Revalidate stored evidence and invoice before applying, and prevent duplicate credits.
- Native control enforcement must be observed, not inferred from instructions. Agent Identity remains optional and is never represented as enabled without proof.
- Arabic and English agents/KB; masculine Arabic UI instructions. IDs and money remain consistent when switching language.
- No credentials in Git, logs, exported YAML, or reports. No real customer data or unsolicited messages.
- Server update is authorized; identify exact existing hosting application and revision first. Preserve credential bindings and trace destinations. Do not falsely claim deployment from local tests.

## Tasks
1. Establish baseline and isolated checkout; resolve hosting, CLI inventory and supported multilingual embeddings. Fix missing local dependencies in an isolated venv. Record baseline outcome.
2. Add synthetic outage evidence and read-only external partner profile, preserving trial/account/network profiles. Tests: exact duration, scope/exclusions, unknown IDs, both protocol adapters and Arabic/English.
3. Add persistent case/quote/credit ledger API with separate privileged workflow credential; quote calculation, stale quote rejection, forbidden direct execution, rejection and idempotence tests. Interface: case_id -> quote_id -> workflow decision -> immutable credit receipt.
4. Add equivalent Arabic/English policy KB documents and explicit multilingual embedding config; import, wait for readiness and test retrieval in both languages.
5. Author native tools, agents and workflow: retrieve case/evidence, assess, branch, user approval, commit, receipt and message draft. Agent-accessible tools cannot decide human approval. Native form labels bilingual if Arabic locale translation is unsupported. Validate SDK schema/import and actual pause/resume behavior.
6. Bind PII control to new agents only; demonstrate redaction using synthetic email/phone and inspect control trace. Optional Agent Identity is a separate readiness check.
7. Update authorized external deployment when hosting access is available; test real endpoints/native collaboration. Capture sanitized run IDs, workflow status and control evidence; provide bilingual filming script and readiness ledger.

## Review focus
Authorization boundaries, workflow bypass, persisted state across restart, duplicate concurrent credits, incompatible fixture/profile changes, secrets in artifacts, bilingual retrieval failures, differences between registration/import and a working deployed end-to-end journey.

## Evidence ledger
- Isolated clone from GitHub master created on 2026-11-18. Existing local clone contains staged user work and is untouched.
- Existing baseline initially fails because global Python lacks langchain_openai; install project dependencies in local venv before assessing regressions.
- Active environment ISYS-Event-Nov2026 confirmed. Native PII Filter, Regex Pattern and other control artifacts available.
- Ruling: retain the existing external trace target unless explicitly configuring a new event-specific deployment; changing the code must not silently reroute the existing workshop telemetry.
- Backend/external slice: 25 tests pass, including A2A/chat adapters, rejection, stale/expired quotes, concurrent/idempotent execution and separate credential enforcement.
- Final independent review: two Important findings fixed with observed RED→GREEN tests: rejection of a second quote now reports the current invoice; separate-token guard compares against the resolved reader credential. Full suite 25/25 green after fixes. No Minor findings.
- Native KB imported and ready. Policy/communications/copilot, workflow and PII binding imported. English retrieval plus Arabic switch on the same thread verified correct 900/90/810/50.
- Ruling: all demo credits require human review, including any below the automatic cap — stricter than the fictional policy, avoids introducing an unrequested automatic posting route. Cost: below-cap automation is not demonstrated.
- Approver resolved from matching tenant profile: amotawea@isys.ai / IBMid-698000U0QU. This is the preparation account, so distinct-actor separation remains unverified until a second user is used.
- Native PII binding exists but first Draft probe returned unredacted synthetic data; enforcement is not yet confirmed. Diagnose with live release and actual control spans before filming.
- Server read-only console verified Ready and old revision/image retained for rollback. Existing local IBM IAM API key is disabled; do not use it further. Console login is available.
- Controls runtime confirmed: native PII input redaction trace 6876fbecdf9a9690f9620935ef8caedc, native Regex bulk-export block trace e2f66717c3297cae9fa1320cd53fb7da with allow=false. Output hook is still unverified; filming scope corrected accordingly.
- Deployment helper independent review found mutable tag reuse, inadequate concurrency guard and incorrect revision path; fixed with three observed RED→GREEN contract tests. Helper now uses a unique build tag, verified source commit and digest, exact entity-tag guard, and status_details.latest_ready_revision matching the new target revision.
- User selected authenticated Cloud Shell deployment, refreshed event Orchestrate login, and then explicitly chose to run the deployment command personally. Server update is pending that handoff; no successful cloud build/revision is claimed.
- Ruling: privileged endpoint trusts the protected workflow capability, not a cryptographic native task-completion proof — documented boundary. Cost: platform administrators holding the capability remain trusted; this is not an Agent Identity demonstration.
