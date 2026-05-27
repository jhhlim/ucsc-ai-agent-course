"""Load and validate project environment for Gemini ADK examples."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_SRC_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _SRC_DIR / ".env"

_PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "<your key>",
        "your key",
        "<your api key>",
        "YOUR_API_KEY_HERE",
        "changeme",
    }
)


def load_project_env() -> Path:
    """Load src/.env regardless of the current working directory."""
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=True)
    else:
        load_dotenv(override=True)
    return _ENV_FILE


def require_google_api_key() -> str:
    """Ensure GOOGLE_API_KEY is set to a real Gemini API key."""
    api_key = (os.getenv("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
    if api_key in _PLACEHOLDER_VALUES or not api_key.startswith("AIza"):
        env_hint = f"Edit {_ENV_FILE} and set GOOGLE_API_KEY to your key."
        raise SystemExit(
            "\nGOOGLE_API_KEY is missing or still a placeholder.\n"
            f"  {env_hint}\n"
            "  Create a key: https://aistudio.google.com/apikey\n"
        )
    os.environ["GOOGLE_API_KEY"] = api_key
    return api_key


def get_gemini_model(default: str = "gemini-2.5-flash") -> str:
    return (os.getenv("GEMINI_MODEL") or default).strip()
