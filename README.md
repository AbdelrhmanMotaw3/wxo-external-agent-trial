# watsonx Orchestrate external agent trials

One FastAPI + LangGraph service that watsonx Orchestrate can call over:

- **Chat completions** (`POST /chat/completions`, SSE streaming)
- **A2A 0.3.0** (JSON-RPC at `/`, agent card at `/.well-known/agent-card.json`)

The LLM is **OpenRouter**. You can host the service on **IBM Cloud Code Engine** or **Render**. Traces can export over OTLP/HTTP for both **use and observability** and **observability only**. Export stays off until `OTEL_EXPORT_URL` and `TENANT_ID` are set.

## Endpoints

| Path | Purpose |
| --- | --- |
| `GET /health` | Health check. Does not call the LLM. |
| `POST /chat/completions` | Orchestrate external_chat collaborator |
| `GET /.well-known/agent-card.json` | A2A discovery |
| `POST /` | A2A JSON-RPC (`message/send`, `message/stream`) |
| `POST /demo/chat` | Observability-only chat demo (tags `CHAT_OBS_AGENT_ID`) |
| `POST /demo/a2a` | Observability-only A2A demo (tags `A2A_OBS_AGENT_ID`) |

Auth for protected routes: `Authorization: Bearer <AGENT_AUTH_TOKEN>` or `X-API-Key: <AGENT_AUTH_TOKEN>`.

For the two-specialist Telecom Customer Support exercise, use the [lab guide](orchestrate/telecom/README.md).

## Local run

```powershell
cd "D:\External agents"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env — at minimum OPENROUTER_API_KEY and AGENT_AUTH_TOKEN
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Smoke chat (non-stream):

```powershell
curl -X POST http://localhost:8080/chat/completions `
  -H "Authorization: Bearer change-me-trial-token" `
  -H "Content-Type: application/json" `
  -d '{"model":"openai/gpt-4o-mini","stream":false,"messages":[{"role":"user","content":"Look up the account status"}]}'
```

Agent card:

```powershell
curl http://localhost:8080/.well-known/agent-card.json
```

## Deploy on Render

1. Push this folder to a Git repo (or connect the local folder in the Render dashboard).
2. Create a Blueprint from [`render.yaml`](render.yaml), or create a Python Web Service with:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set secrets: `OPENROUTER_API_KEY`, `AGENT_AUTH_TOKEN`, `PUBLIC_URL` (your `https://….onrender.com` URL, no trailing slash).
4. Confirm `GET https://<host>/health` returns `ok`.

## Deploy on IBM Cloud Code Engine

Build from this repository with the root [`Dockerfile`](Dockerfile). Code Engine builds the image, stores it in IBM Cloud Container Registry, and runs it. Official steps: [Deploying an app from repository source code](https://cloud.ibm.com/docs/codeengine?topic=codeengine-app-source-code), [environment variables](https://cloud.ibm.com/docs/codeengine?topic=codeengine-envvar), [secrets](https://cloud.ibm.com/docs/codeengine?topic=codeengine-secret), and [scaling](https://cloud.ibm.com/docs/codeengine?topic=codeengine-app-scale).

Push these deployment files to `master` on `https://github.com/AbdelrhmanMotaw3/wxo-external-agent-trial`: `Dockerfile`, `.dockerignore`, `.gitignore`, `.env.example`, `README.md`, `app/main.py`, and `app/graph.py`. Do not commit `.env` or `trace-*.json`.

In the Code Engine console:

1. Open your project, then **Start creating** → **Application**.
2. Name the app, for example `wxo-external-agent-trial`.
3. Choose **Build container image from source code** and specify the Git repository. Use the branch that contains the Dockerfile. Code repo access can be **None** while the repo is public.
4. Build strategy: **Dockerfile**. Build context is the repository root (leave the context directory empty). Dockerfile path: `Dockerfile`.
5. Output registry: an IBM Cloud Container Registry location in your account. Choose **Code Engine managed secret** when Code Engine is allowed to create the registry access secret, and let it create or select the registry namespace.
6. Runtime:
   - Endpoint visibility: **public**
   - Listening port: **8080**
   - CPU: **1 vCPU**
   - Memory: **2 GB**
   - Timeout: **300 seconds**
   - For the workshop demo: minimum instances **1**, maximum instances **1**
7. Create a Code Engine secret for `OPENROUTER_API_KEY` and `AGENT_AUTH_TOKEN`. On the application, add environment variables that reference those secret keys. Literal values are also supported, but secrets keep the key and token out of the revision form. See [Defining environment variables](https://cloud.ibm.com/docs/codeengine?topic=codeengine-envvar) and [Creating secrets](https://cloud.ibm.com/docs/codeengine?topic=codeengine-secret).
8. Set `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1` and `OPENROUTER_MODEL=openai/gpt-4o-mini` as literal environment variables. Leave observability variables empty for the first revision.
9. Create the application and wait until the revision is **Ready**. Open the application URL and check `GET /health`.

After the first deploy, copy the generated URL (no trailing slash) into `PUBLIC_URL`, save the application, and wait for the new revision before A2A discovery. The agent card is built at process start from `PUBLIC_URL`.

| Check | URL |
| --- | --- |
| Health | `https://<app-host>/health` |
| Agent card | `https://<app-host>/.well-known/agent-card.json` |
| A2A JSON-RPC | `POST https://<app-host>/` |
| Chat completions | `POST https://<app-host>/chat/completions` |

Register in watsonx Orchestrate only after `/health` succeeds. See [Connect to external agents](https://developer.watson-orchestrate.ibm.com/agents/connect_agent).

- Chat completions service URL: `https://<app-host>/chat/completions`
- A2A 0.3.0 service URL: `https://<app-host>` (the agent-card root, not `/chat/completions`)
- Authentication: Bearer token. Use the same value as `AGENT_AUTH_TOKEN`.

A2A tasks are stored in memory. A restart clears them, and they are not shared if you later run more than one instance. Keep max instances at 1 for this demo. After the workshop, set minimum instances back to **0** so the app can scale to zero when idle. The next request starts a new instance.

Add `TENANT_ID`, `OTEL_EXPORT_URL`, `ENVIRONMENT_NAME`, and the IAM or MCSP credential only after a plain chat call and an A2A call both succeed. If either `OTEL_EXPORT_URL` or `TENANT_ID` is unset, the process still serves traffic and skips trace export.

## Register in watsonx Orchestrate

Replace placeholders in [`orchestrate/*.yaml`](orchestrate) with the public Code Engine or Render URL and token, or set them in the UI.

### A. Use and observability (collaborators)

AI Gateway → Agent directory → Add agent → **Import for use and observability**

1. **Chat completions**
   - Protocol: External agent via chat completion
   - Service URL: `https://<host>/chat/completions`
   - Auth: Bearer / API key = `AGENT_AUTH_TOKEN`
   - Copy the assigned **Agent ID** into the application environment as `CHAT_AGENT_ID`
2. **A2A**
   - Protocol: External agent via A2A protocol (version **0.3.0**)
   - Service URL: `https://<host>` (agent card root)
   - Enable streaming + send conversation history; leave push notifications off
   - Copy **Agent ID** → `A2A_AGENT_ID`

Or import YAML after substituting values:

```powershell
orchestrate env activate <ENV>
orchestrate agents import -f orchestrate/chat_agent.yaml
orchestrate agents import -f orchestrate/a2a_agent.yaml
orchestrate agents import -f orchestrate/trial_router.yaml
orchestrate agents deploy -n external_agent_trial_router
```

Ask the router:

- `Run a chat trial and look up the account status.`
- `Run an a2a trial and look up observability info.`

### B. Observability only (not collaborators)

AI Gateway → Agent directory → Add agent → **Import for observability only**

1. Register a display name for the chat trial → copy Agent ID → `CHAT_OBS_AGENT_ID`
2. Register a display name for the A2A trial → copy Agent ID → `A2A_OBS_AGENT_ID`
3. Set `TENANT_ID`, `OTEL_EXPORT_URL`, and IAM/MCSP credentials on the host, then start a new revision or restart.

Generate traces without Orchestrate calling the agent:

```powershell
curl -X POST https://<host>/demo/chat `
  -H "Authorization: Bearer <AGENT_AUTH_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message":"Look up observability info"}'

curl -X POST https://<host>/demo/a2a `
  -H "Authorization: Bearer <AGENT_AUTH_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message":"Look up the account status"}'
```

Check **Analyze → [agent] → Overview / Conversations**.

## Trace env reference

For the IBM Cloud implementation, actual model/tool spans, automatic IAM token refresh,
runtime secret configuration, verification, and rollback, see
[IBM Cloud tracing](docs/IBM_CLOUD_TRACING.md).

| Variable | Role |
| --- | --- |
| `TENANT_ID` | From instance CRN / `WO_Meta` |
| `OTEL_EXPORT_URL` | `…/instances/<id>/v1/orchestrate/inject/traces` |
| `ENVIRONMENT_NAME` | `draft` or `live` |
| `API_KEY` + `TOKEN_URL` | IBM Cloud IAM |
| `AUTH_TYPE=MCSP_v2` + `X_API_KEY` + `MCSP_V2_TOKEN_URL` | MCSP v2 |

When Orchestrate invokes the service it may send `traceparent`; the app continues
that context. A shared platform/external trace must be verified, not assumed.
Chat SSE tool events are a separate channel from exported OpenTelemetry spans.

## Project layout

```
app/
  main.py          FastAPI routes
  graph.py         LangGraph + OpenRouter + trial_lookup tool
  chat.py          Chat completions + SSE events
  a2a_server.py    A2A 0.3 agent card + JSON-RPC
  tracing.py       OTLP export
  auth.py          Bearer / X-API-Key check
orchestrate/       External + router YAML for ADK import
render.yaml        Render Blueprint
Dockerfile         Code Engine / container image
.dockerignore      Files kept out of the image
```

## Notes

- External agents are collaborators of a native agent; chat with the trial router, not the externals alone.
- Chat streaming emits `thread.message.delta` and `thread.run.step.delta` (thinking / tool_calls / tool_response) so `enable_cot` can show steps.
- If `OTEL_EXPORT_URL` / `TENANT_ID` are empty, the agent still answers and skips export.
