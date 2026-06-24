"""LangSmith tracing setup for HW3 mortgage agents (LiteLLM + orchestrator)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_SRC_ENV = Path(__file__).resolve().parent.parent.parent / "src" / ".env"
load_dotenv(_SRC_ENV)
load_dotenv()

DEFAULT_PROJECT = "ucsc-hw3-mortgage"
ORG_ID = "0e0ab241-41c6-425d-afbb-dbeafa0df253"


def langsmith_project_url(project: str | None = None) -> str:
    proj = project or os.getenv("LANGSMITH_PROJECT", DEFAULT_PROJECT)
    return f"https://smith.langchain.com/o/{ORG_ID}/projects/p/{proj}"


def configure_langsmith_tracing(project: str | None = None) -> bool:
    """Enable LangSmith tracing for LiteLLM and @traceable spans.

    Returns True when tracing is active, False when API key is missing.
    """
    api_key = (os.getenv("LANGSMITH_API_KEY") or "").strip()
    if not api_key:
        return False

    project_name = project or os.getenv("LANGSMITH_PROJECT", DEFAULT_PROJECT)
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = project_name

    # LiteLLM → LangSmith callback (used by Google ADK LiteLlm model calls)
    try:
        import litellm

        litellm.success_callback = ["langsmith"]
        litellm.failure_callback = ["langsmith"]
        litellm.langsmith_batch_size = 1  # flush quickly for local eval runs
    except ImportError:
        pass

    return True


def require_langsmith() -> str:
    if not configure_langsmith_tracing():
        raise SystemExit(
            "\nLANGSMITH_API_KEY is missing.\n"
            f"  1. Sign in at https://smith.langchain.com/o/{ORG_ID}/projects\n"
            "  2. Settings → API Keys → create a key\n"
            f"  3. Add to {_SRC_ENV}:\n"
            f"     LANGSMITH_API_KEY=\"lsv2_...\"\n"
            f"     LANGSMITH_PROJECT=\"{DEFAULT_PROJECT}\"\n"
            "     LANGSMITH_TRACING=true\n"
        )
    return os.environ["LANGSMITH_PROJECT"]
