# English-only service recovery demo implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement these tasks sequentially. Read-only review can run independently.

**Goal:** Make the active demonstration entirely English and usable through ordinary employee requests.

**Architecture:** Keep the existing native router, specialists, knowledge base, protected workflow and external provider. Move execution safeguards into agent instructions and the workflow; employee prompts express business intent. Retain existing technical IDs and connection capabilities. An Egyptian-Arabic presentation adapter is a separate future option.

**Tech stack:** Python 3.12, FastAPI, SQLite, LangGraph, watsonx Orchestrate ADK 2.18.2, Code Engine.

**Spec:** The user's request in this conversation: all names, details and data in English; short natural employee prompts without repeated defensive clauses.

## Constraints and verification

- Preserve the 900/90/810 service-credit calculation, policy version and strict human decision boundary.
- Keep privileged settlement off chat agents, distinct capabilities, PII detectors and export restriction.
- Retain existing agent/KB/connection technical IDs and preserve external credentials during metadata updates.
- Keep original KAI repository and existing account application outside scope.
- Recompile the native form and its label-dependent output mapping together.
- Replace the KB document set with policy-en.txt, verify ready and verify Arabic documents removed.
- Update the deployed external backend before asserting its data is English.
- Use natural English employee requests in runtime verification; a model-written approval remains insufficient.

## Tasks

- [x] Add a failing English-content/case-contract regression check.
- [x] Convert active source data, agent metadata/instructions, tools, KB, form, controls and runbook.
- [x] Preserve storage compatibility while exposing a canonical English customer name.
- [x] Run affected backend tests and regenerate the compiled workflow.
- [x] Import English native assets and verify current target and preserved credentials.
- [x] Review, publish reviewed source and deploy the English backend to the existing network application.
- [x] Verify English retrieval, external evidence, natural employee workflow requests and real rejection/approval.
- [x] Leave a clean filming baseline and report any remaining deployment or session blockers accurately.

## Execution evidence

- English source/case regression checks first failed on the bilingual source and missing canonical name; they now pass.
- Combined local verification: 27 application/English tests and 4 deployment contract tests passed; git diff --check passed.
- Same KB ID is ready with only policy-en.txt. Existing native agent IDs, connections, external bearer and control bindings were retained.
- Natural eligibility retest 3ef11571-a730-4bd3-8272-c15350650677 called the quote tool, policy collaborator and knowledge retrieval, returning 90 EGP and S1-S4.
- Native English rejection instance 44b036c5-d00c-416e-93cb-5d55442a1c72 completed with rejected/0/900.
- Native English approval instance cd53d6c8-c476-4905-ab25-34b9d34eb2b8 completed with applied/90/810 and receipt CR-0c5c2b3f993f4239.
- English export trace fb5ccd54e9bd6ac342e68307ddc3c0d0 records RegexPattern allow=false. Privacy input trace 44857942386fa3f600f1b151b815b87a records redaction before processing.
- Ruling: remove the sample-contact diagnostic tool from Customer Communications after a natural draft request selected it incorrectly. The copilot retains the diagnostic tool; privacy controls remain bound to all three agents. Retest without a supplied receipt requests the receipt and calls no tool (run 9c5f123e-3edc-4f6a-b690-9aed0d858832).
- Read-only source and deployment-helper reviews found no material issues.
- User-operated English deployment returned ready on telecom-network-00008 with image digest sha256:3f08ecc064a0bb960265de361bfd45625cc672d72e5a0ff4fb1b631791b792c0. Independent public health check observed 2026-11-18-en-v2 and network_service.
- Post-deployment native case run aebea48e-5916-4fa3-a575-7d471a709757 returned canonical customer_name Nour Ahmed, English history, invoice 900, version 1 and credit_receipt null in the raw case tool response. No legacy customer_ar/customer_en fields remained.
- Post-deployment external run 7382f83a-b036-4b91-83c6-7113934047fa executed A2A and returned English evidence for the confirmed 72-hour restored outage. Eligibility run 117fb96b-7f28-4faf-bfea-3408c5fe6fe2 prepared the real 90 EGP quote and retrieved the English policy, preserving the 900 starting invoice.
- Native input_required and working inventories were empty. No new settlement was run after deployment. The clean filming baseline is ready in Draft; prior English approval/rejection evidence remains recorded above. Live publishing and a new visual UI take are separate from these API/MCP checks.
