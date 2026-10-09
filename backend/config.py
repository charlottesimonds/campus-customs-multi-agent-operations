"""Model and run settings for the Campus Customs agent team.

PORTKEY_API_KEY is read from the environment or the nearest .env file above
this folder. No key is ever stored in source code.
"""

import os

from dotenv import find_dotenv, load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

load_dotenv(find_dotenv())  # existing environment variables take precedence

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# The only model this project uses. It is deliberately not configurable.
MODEL_NAME = "gpt-6-luna"
# Portkey reports the served deployment name (e.g. "gpt-6-luna-global"); every
# response is checked against this prefix so a silent fallback is caught.
SERVED_MODEL_PREFIX = "gpt-6-luna"

MODEL_SETTINGS = {"max_tokens": 4_000, "timeout": 120}

# Delegation guards (see team.py).
MAX_DELEGATION_DEPTH = 3  # e.g. Boss -> Inventory -> Accounting -> Facilities, and no deeper
MAX_DELEGATIONS_PER_TICKET = 12

# One budget shared by every agent run inside a single ticket.
TICKET_USAGE_LIMITS = UsageLimits(request_limit=60, tool_calls_limit=80)


class ModelNotConfigured(RuntimeError):
    """Raised when PORTKEY_API_KEY is missing."""


def build_model() -> OpenAIResponsesModel:
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise ModelNotConfigured("PORTKEY_API_KEY is not set. Add it to a .env file at the project root.")
    client = AsyncOpenAI(api_key=api_key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-api-key": api_key})
    # GPT-6 models only accept function tools through the Responses API.
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
