"""Put hw3 on sys.path before any mortgage_agents imports (adk web/run)."""
import sys
from pathlib import Path

_HW3_ROOT = Path(__file__).resolve().parent.parent
if str(_HW3_ROOT) not in sys.path:
    sys.path.insert(0, str(_HW3_ROOT))
