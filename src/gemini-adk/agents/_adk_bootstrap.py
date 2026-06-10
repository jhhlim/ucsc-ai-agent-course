"""Put gemini-adk on sys.path so agents can import env_config under adk web/run."""
import sys
from pathlib import Path

_GEMINI_ADK_ROOT = Path(__file__).resolve().parent.parent
_root = str(_GEMINI_ADK_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)
