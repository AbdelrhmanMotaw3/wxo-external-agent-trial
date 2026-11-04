# Telecom customer support lab

Use watsonx Orchestrate to investigate a home internet complaint. A native router delegates to two LangGraph agents hosted on Code Engine. The Account agent returns the customer's subscription, billing state and area. The Network agent uses the area and service to check incidents and maintenance. The router combines the results and preserves their record references.

## Data and tools

All records in `app/telecom_data/` are synthetic. They describe the same fixed snapshot, **15 October 2026 at 10:00 UTC**, so the expected results do not change on workshop day.

| Profile | Tools | Records |
| --- | --- | --- |
| `customer_account` | `get_customer_account`, `get_subscription`, `get_invoices` | 20 customers, 20 subscriptions, 6 plans, 40 invoices |
| `network_service` | `get_service_area`, `get_active_incidents`, `get_planned_maintenance` | 8 areas, 10 incidents, 3 maintenance records |

Each specialist exposes only its own tools. Each tool returns structured records and source IDs. The FastAPI service appends an execution footer with the specialist, protocol, tool outcome and record references taken from LangGraph tool outputs. The footer lists records retrieved during the turn. It does not certify that every sentence the model wrote follows from those records. Check the cited records when assessing the answer.

## Deploy two Code Engine applications

1. Build this revision once with the repository Dockerfile, then use the same image reference for both applications. The image copies `app/`, including the fixtures. Use an image tag or digest that identifies the lab revision.
2. Update the existing `application-6b` with the new image and set `AGENT_PROFILE=customer_account`. Create a public application such as `telecom-network` from that same image with `AGENT_PROFILE=network_service`. Use port `8080` and a maximum of one instance for each app's in-memory A2A task store. If starting in a new project, create both applications.
3. Set each app's `PUBLIC_URL` to its own HTTPS base URL. Reference secret keys for `OPENROUTER_API_KEY` and `AGENT_AUTH_TOKEN`. The tokens can be different for the two apps. For local testing, start Uvicorn in separate processes with matching profiles and distinct ports.
4. Check `/health` for the expected `agent_profile`, then check `/.well-known/agent-card.json` for the specialist's title and base URL. Each app serves Chat Completions at `/chat/completions` and A2A JSON-RPC at `/`. Start with non-streaming calls.

The original demo profile is selected by default when `AGENT_PROFILE` is omitted.

## Compare the same lookup over both protocols

Use these calls as a smoke test before setup or as a short comparison after the main Orchestrate exercise. In Bash, set `base` to the Network app URL without a trailing slash. Enter the Network app token when prompted.

```bash
read -rs -p 'Network agent token: ' token
printf '\n'
curl -fsS "$base/chat/completions" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  --data '{"stream":false,"messages":[{"role":"user","content":"Check active home_internet incidents in AREA-003."}]}' \
  | jq -er '.choices[0].message.content'

curl -fsS "$base/" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  --data '{
    "jsonrpc":"2.0","id":"telecom-lab-1","method":"message/send",
    "params":{"message":{"messageId":"telecom-message-1","role":"user",
      "parts":[{"kind":"text","text":"Check active home_internet incidents in AREA-003."}]}}
  }' \
  | jq -er 'select(.result.status.state == "completed") | .result.artifacts[0].parts[0].text'
unset token
```

Both responses should cite `incidents.json#INC-024`. Chat Completions returns an assistant message. A2A returns a completed task with an answer artifact. Use the Account app URL and token with a customer lookup to run the same comparison for Account.

## Connect the specialists to Orchestrate

Make private copies of `account_chat.yaml`, `network_a2a.yaml`, and `router.yaml`. Replace the URL placeholders with each app's own base URL without a trailing slash. Replace the token placeholders with each app's `AGENT_AUTH_TOKEN`. Use a model available in your target instance that supports the router's agent style. Keep the resolved files outside Git. [IBM external agent documentation](https://developer.watson-orchestrate.ibm.com/agents/connect_agent)

Activate the target ADK environment and import the two collaborator files with `orchestrate agents import -f <resolved-file>`. Import `router.yaml` last and test the router in preview. The router calls Account via Chat Completions and Network via A2A. The other templates are available for a separate Orchestrate exercise.

## Lab exercises and expected results

Start with: “Customer CUST-1007 says their home internet stopped working. Check their account and network status and show the supporting records.”

| Customer | Expected assessment |
| --- | --- |
| `CUST-1007` | Subscription `SUB-1007` active, invoices paid, matching active home internet incident `INC-024` in `AREA-003`. The incident is a likely cause and its restoration time is an estimate. |
| `CUST-1008` | Subscription suspended, with overdue invoice `INV-1008-10`. No matching active home internet incident in `AREA-004`. |
| `CUST-1009` | Future maintenance `MNT-011` in `AREA-005`. No matching active incident at the snapshot, so the current cause remains unconfirmed. |
| `CUST-1010` | Resolved incident `INC-025` does not appear as active. No matching current incident in `AREA-006`. |
| `CUST-1011` | Active incident `INC-026` affects mobile data, so it is excluded for home internet in `AREA-007`. |
| `CUST-1012` | Both service suspension and a matching active network incident are present. Report both. |
| `CUST-9999` | Customer not found. Ask for a correct ID and do not infer a service area. |

Inspect the two collaborator calls in Orchestrate's execution view. Then use the two `curl` requests above to run the same `AREA-003` lookup against the Network agent and compare the response envelopes and record IDs. For an area-only request in Orchestrate, give the router both the area ID and the service.
