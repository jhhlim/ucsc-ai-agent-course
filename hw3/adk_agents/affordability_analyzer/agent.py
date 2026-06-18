import sys
from pathlib import Path

_HW3_ROOT = Path(__file__).resolve().parents[2]
if str(_HW3_ROOT) not in sys.path:
    sys.path.insert(0, str(_HW3_ROOT))

from mortgage_agents.builders import affordability_analyzer_agent as root_agent
