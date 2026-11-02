"""Runtime configuration from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


PUBLIC_URL = (env("PUBLIC_URL", "http://localhost:8080") or "http://localhost:8080").rstrip(
    "/"
)
AGENT_AUTH_TOKEN = env("AGENT_AUTH_TOKEN", "change-me-trial-token") or "change-me-trial-token"
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1") or (
    "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL = env("OPENROUTER_MODEL", "openai/gpt-4o-mini") or "openai/gpt-4o-mini"

# Use-and-observability Agent IDs (collaborators)
CHAT_AGENT_ID = env("CHAT_AGENT_ID")
A2A_AGENT_ID = env("A2A_AGENT_ID")

# Observability-only Agent IDs (not collaborators)
CHAT_OBS_AGENT_ID = env("CHAT_OBS_AGENT_ID")
A2A_OBS_AGENT_ID = env("A2A_OBS_AGENT_ID")

TENANT_ID = env("TENANT_ID")
ENVIRONMENT_NAME = env("ENVIRONMENT_NAME", "draft") or "draft"
OTEL_EXPORT_URL = env("OTEL_EXPORT_URL")
AUTH_TYPE = env("AUTH_TYPE", "")
API_KEY = env("API_KEY")
TOKEN_URL = env("TOKEN_URL", "https://iam.cloud.ibm.com/identity/token")
X_API_KEY = env("X_API_KEY")
MCSP_V2_TOKEN_URL = env("MCSP_V2_TOKEN_URL")

SERVICE_NAME = env("SERVICE_NAME", "wxo-external-agent-trial") or "wxo-external-agent-trial"
SERVICE_VERSION = env("SERVICE_VERSION", "1.0.0") or "1.0.0"
