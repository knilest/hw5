"""The one model every agent uses: gpt-6-luna through Portkey."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Look for .env in HW 5, then the course folder above it.
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

# Assignment rule: only gpt-6-luna, for every agent. Not configurable on purpose.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

_model: OpenAIResponsesModel | None = None


def get_model() -> OpenAIResponsesModel:
    global _model
    if _model is None:
        api_key = os.getenv("PORTKEY_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("PORTKEY_API_KEY is not set (put it in a .env file).")
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=PORTKEY_BASE_URL,
            default_headers={"x-portkey-api-key": api_key},
        )
        _model = OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
    return _model
