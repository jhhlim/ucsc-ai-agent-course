"""LLM backend configuration — defaults to Doubleword via LiteLLM."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from google.adk.planners import BuiltInPlanner

_SRC_ENV = Path(__file__).resolve().parent.parent.parent / "src" / ".env"
load_dotenv(_SRC_ENV)
load_dotenv()


def get_doubleword_litellm() -> LiteLlm:
    """Build a LiteLlm client pointed at the Doubleword OpenAI-compatible API."""
    api_key = (os.getenv("DOUBLEWORD_API_KEY") or "").strip()
    model = (os.getenv("DOUBLEWORD_MODEL") or "openai/Qwen/Qwen3.6-35B-A3B-FP8").strip()
    api_base = (os.getenv("DOUBLEWORD_API_URL") or "https://api.doubleword.ai/v1").strip()

    if not api_key or api_key in {"<your key>", "YOUR_API_KEY_HERE"}:
        raise SystemExit(
            "\nDOUBLEWORD_API_KEY is missing.\n"
            f"  Add it to {_SRC_ENV} (see src/env.example).\n"
        )

    return LiteLlm(
        model=model,
        api_base=api_base,
        api_key=api_key,
        include_reasoning=False,
    )


def get_planner() -> BuiltInPlanner:
    return BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
            thinking_budget=0,
        ),
    )
