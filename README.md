# watsonx Orchestrate external agent trials

One FastAPI + LangGraph service that watsonx Orchestrate can call over:

- **Chat completions** (`POST /chat/completions`, SSE streaming)
- **A2A 0.3.0** (JSON-RPC at `/`, agent card at `/.well-known/agent-card.json`)

Hosted on **Render**, LLM via **OpenRouter**. Traces export over OTLP/HTTP for both **use and observability** and **observability only**.

## Endpoints

| Path | Purpose |
| --- | --- |
| `GET /health` | Render health check |
| `POST /chat/completions` | Orchestrate external_chat collaborator |
| `GET /.well-known/agent-card.json` | A2A discovery |
| `POST /` | A2A JSON-RPC (`message/send`, `message/stream`) |
| `POST /demo/chat` | Observability-only chat demo (tags `CHAT_OBS_AGENT_ID`) |
| `POST /demo/a2a` | Observability-only A2A demo (tags `A2A_OBS_AGENT_ID`) |

Auth for protected routes: `Authorization: Bearer <AGENT_AUTH_TOKEN>` or `X-API-Key: <AGENT_AUTH_TOKEN>`.

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

## Register in watsonx Orchestrate

Replace placeholders in [`orchestrate/*.yaml`](orchestrate) with your Render URL and token, or set them when importing / through the UI.

### A. Use and observability (collaborators)

AI Gateway → Agent directory → Add agent → **Import for use and observability**

1. **Chat completions**
   - Protocol: External agent via chat completion
   - Service URL: `https://<host>/chat/completions`
   - Auth: Bearer / API key = `AGENT_AUTH_TOKEN`
   - Copy the assigned **Agent ID** → Render env `CHAT_AGENT_ID`
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
3. Set `TENANT_ID`, `OTEL_EXPORT_URL`, and IAM/MCSP credentials on Render, then restart.

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

| Variable | Role |
| --- | --- |
| `TENANT_ID` | From instance CRN / `WO_Meta` |
| `OTEL_EXPORT_URL` | `…/instances/<id>/v1/orchestrate/inject/traces` |
| `ENVIRONMENT_NAME` | `draft` or `live` |
| `API_KEY` + `TOKEN_URL` | IBM Cloud IAM |
| `AUTH_TYPE=MCSP_v2` + `X_API_KEY` + `MCSP_V2_TOKEN_URL` | MCSP v2 |

When Orchestrate invokes the service it may send `traceparent`; the app continues that context so spans nest under the platform trace.

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
```

## Notes

- External agents are collaborators of a native agent; chat with the trial router, not the externals alone.
- Chat streaming emits `thread.message.delta` and `thread.run.step.delta` (thinking / tool_calls / tool_response) so `enable_cot` can show steps.
- If `OTEL_EXPORT_URL` / `TENANT_ID` are empty, the agent still answers and skips export.
