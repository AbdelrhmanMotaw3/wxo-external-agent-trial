# IBM Cloud tracing for the telecom external agents

This implementation targets the existing Toronto IBM Cloud Orchestrate instance.
AWS and on-premises trace authentication are not verified by this change.

## What this adds

- One execution span per Chat Completions request or A2A execution.
- A child `agent.graph` span containing actual-timed `gen_ai.chat` and `tool_call <name>` spans. These are created by LangChain callbacks at execution time, not reconstructed with estimated timestamps after execution.
- Model token usage when supplied by the provider. The OpenRouter client requests final streaming usage chunks explicitly. Missing usage remains missing; the code does not invent token counts.
- Agent/session attribution on child spans, and incoming W3C trace context when supplied.
- Thread-safe IAM access-token caching, refresh before expiry, and one retry after an ingestion HTTP 401. The rejected token is invalidated, and the identical protobuf batch is resent once.
- Optional bounded input/output capture, plus shutdown flushing.

The existing Chat Completions SSE tool events and evidence footer remain separate from OpenTelemetry. Seeing tool steps in chat does not by itself prove that separate external tool spans were ingested.

## Configuration for the existing environment

These identifiers come from the live environment reviewed on 5 November. Re-resolve agent IDs if agents have been deleted and recreated.

```text
Orchestrate CLI environment: ISYS-Ext
Instance URL:
https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/56d1b637-1997-463b-92e8-16e5c303d8eb

OTEL_EXPORT_URL:
https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/56d1b637-1997-463b-92e8-16e5c303d8eb/v1/orchestrate/inject/traces

TENANT_ID:
1923f9ccee2d4cef9db7e6ef72f7c133_56d1b637-1997-463b-92e8-16e5c303d8eb

WORKSPACE_ID: 00000000-0000-0000-0000-000000000001
ENVIRONMENT_NAME: draft
TOKEN_URL: https://iam.cloud.ibm.com/identity/token
```

| Code Engine application | Profile | Trace service name | Agent ID variable | Agent ID |
|---|---|---|---|---|
| application-6b | customer_account | telecom-customer-account | CHAT_AGENT_ID | 98f36018-e669-41a4-a576-d7b30656ea18 |
| telecom-network | network_service | telecom-network-service | A2A_AGENT_ID | 6bd32245-a8cb-49dd-8af1-4a30478d349a |

`API_KEY` is an IBM Cloud IAM API key authorized for this Orchestrate instance and ingestion endpoint. Store it in a generic Code Engine runtime secret. It is not the inbound `AGENT_AUTH_TOKEN`, the OpenRouter key, or a Container Registry secret.

`TRACE_CAPTURE_CONTENT=false` by default. For this synthetic-data workshop, set it to `true` to capture request/response and tool content. `TRACE_MAX_CONTENT_CHARS=16000` bounds each captured attribute. Error metadata and timings remain available with content capture disabled. Known credential fields, bearer strings and configured secret values are redacted, but this is not a general data-loss-prevention filter.

Do not use the router's Agent ID as the external specialist identity.
Do not copy the old local `.env` trace endpoint into the deployment: it previously referred to a different instance.
`OTEL_RESOURCE_ATTRIBUTES` can coexist with other OpenTelemetry resource metadata; this application explicitly supplies its configured tenant and environment resource attributes to avoid stale values taking precedence.

## Code Engine console activation

Deploy a container image built from this updated source first. Updating variables on the old image will not add model/tool instrumentation or token refresh.

1. Open the existing project `ce-698000u0qu` in Toronto. Keep the existing account/network applications and their existing OpenRouter and inbound-auth settings.
2. In **Secrets and configmaps**, create a **generic** secret named `telecom-tracing-iam` with one key: `API_KEY`. Enter the IAM key privately. This is separate from `wxo-registry-access` and `telecom-network-runtime`.
3. Open `application-6b` -> **Configuration** -> **Environment variables**.
4. Add `API_KEY` using **Reference to key in secret**, selecting `telecom-tracing-iam` and its `API_KEY` key.
5. Add the common non-secret values from the configuration section, then set `CHAT_AGENT_ID` and `SERVICE_NAME` from the Account row. Preserve `AGENT_PROFILE=customer_account` and its existing `PUBLIC_URL`.
6. For the lab, add `TRACE_CAPTURE_CONTENT=true`. Production content capture needs a separate data-handling decision.
7. Save and deploy. Repeat for `telecom-network`, using its Network row, `A2A_AGENT_ID`, `AGENT_PROFILE=network_service` and existing `PUBLIC_URL`.
8. Check that both revisions become Ready. A working `/health` response is not proof of successful telemetry ingestion: authentication happens when spans are exported.

Adding/changing runtime configuration creates a new revision. It does not require a new application. Keep one worker and a maximum of one instance while using the in-memory A2A task store.

## Offline verification

From the project root, using its virtual environment:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

The tests use scripted model responses and mocked IAM/ingestion HTTP calls. They cover expiry refresh, concurrency, 401 retry bounds, real OTLP protobuf serialization, nested span identity and parentage, worker-thread propagation, tool errors/no-match results, content capture, disabled tracing, and the Chat/SSE/A2A/demo API paths. They do not demonstrate Code Engine deployment or live ingestion.

The `/demo/a2a` route remains a simple HTTP demo tagged for observability-only experiments; it is NOT the A2A JSON-RPC protocol. Real A2A requests still use `/`.

## Live verification after activation

1. Ask the router an Account-only question for `CUST-1007`.
2. Ask the router a Network-only question for `AREA-003` / `home_internet`.
3. Open Analytics/Observability for the registered external agents and inspect received traces. UI navigation varies by release.
4. Confirm the exported resource `service.name` identifies the external application, and that `agent.id` identifies the relevant external registration.
5. Confirm separate `gen_ai.chat` and `tool_call ...` observations exist with their own start/end times. JSON text inside a wrapper span's output or chat `step_history` is not equivalent evidence.
6. Confirm provider usage exists only when returned by the model. Test failures and no-match results separately.
7. Check incoming trace IDs against the router trace. One combined trace is conditional on the platform forwarding trace context; registration or matching session IDs alone do not guarantee it.
8. Send an authenticated direct request to the external endpoint. Verify that its external trace arrives even without invoking the router.
9. Exercise export again after the IAM token's real expiration time. Offline clock-controlled tests verify the refresh algorithm, but do not replace a long-running cloud test.

The same regular endpoint can be called by an external client for observability-only use. A dedicated demo endpoint is optional. Export destination and Agent IDs are configured per application process; this version does not automatically choose among multiple Orchestrate tenants.

## Failure handling and rollback

- HTTP 401: one refresh/retry is attempted. Repeated 401s require investigation of the key, instance and access permissions.
- Export transport failures are handled by the OpenTelemetry background exporter and do not intentionally change the agent's answer. A bounded force-flush can delay the response up to the configured flush timeout.
- Invalid explicit tracing configuration is rejected at startup rather than claiming that export is configured successfully.
- HTTP 403 or no visible trace: verify instance access/role and ingestion support. Read access to traces alone does not prove ingestion permissions.
- To turn export off, clear `OTEL_EXPORT_URL` or `TENANT_ID`, then deploy a new revision. The Chat/A2A agent remains usable.
- To revert the code, redeploy the previous known-good image and its previous configuration. Avoid reusing a mutable `latest` tag for verification.

## Official references

- [IBM OpenTelemetry export](https://developer.watson-orchestrate.ibm.com/traces/otel-export)
- [IBM Observability SDK](https://developer.watson-orchestrate.ibm.com/traces/observability-sdk)
- [IBM external-agent control-plane example and refresh discussion](https://developer.ibm.com/articles/watsonx-orchestrate-agentic-control-plane/)
- [IBM Cloud Code Engine environment variables](https://cloud.ibm.com/docs/codeengine?topic=codeengine-envvar)
- [IBM Cloud Code Engine CLI](https://cloud.ibm.com/docs/codeengine?topic=codeengine-cli)

Implementation status must be reported separately from deployment and live ingestion status. Do not mark the Code Engine applications as updated until their image revisions and received external spans have been verified.
