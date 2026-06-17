## Multi-agents examples
This folder contains various of multi-agent examples that are expanded from a single use case

### Sequential
### Parallel
### Loop & Verifier

### Agent Quality (observability with LangSmith)

The `agent_quality/` folder contains a two-agent **Weather & Outfit** pipeline
(`weather_agent` → `outfit_agent`) used to illustrate the agentic quality flywheel:
observability, tracing, and evaluation of a tool-using agent.

The agent is wired up to send traces to [LangSmith](https://smith.langchain.com)
via the official `google-adk` integration. The relevant lines in
`agent_quality/agent.py`:

```python
from langsmith.integrations.google_adk import configure_google_adk

# Configure LangSmith tracing
configure_google_adk()
```

`configure_google_adk()` patches ADK's runtime so every agent invocation, tool
call, and LLM call is exported to LangSmith automatically — no per-call
instrumentation needed.

#### Setup

1. Install the LangSmith client (with the Google ADK integration):

   ```bash
   pip install langsmith
   ```

2. Set the following environment variables (e.g., in `.env`):

   ```bash
   LANGSMITH_API_KEY=ls__...           # from https://smith.langchain.com/settings
   LANGSMITH_TRACING=true              # enables export
   LANGSMITH_PROJECT=weather-outfit    # optional; defaults to "default"
   ```

3. Run the agent via `multi_agent_runner.py` (after updating the import to
   `from agent_quality.agent import root_agent`). Each run will appear as a
   trace in the LangSmith UI with the full agent graph:

   - `weather_agent` node showing the LLM prompt + the `get_weather_forecast`
     tool call (args, raw response, latency).
   - `outfit_agent` node showing the prompt that consumes `{forecast}` and
     the final recommendation.
   - Per-step token usage and total session latency.

#### Why this pipeline is good for evaluation

- **Clean tool boundary** — `get_weather_forecast` returns a flat dict with
  numeric fields, so tool calls are easy to assert against in tests.
- **Structured state handoff** — `output_key="forecast"` means the contract
  between the two agents is observable; you can diff `forecast` JSON across
  runs to catch regressions in the weather agent independently of the outfit
  agent.
- **Deterministic thresholds in the outfit prompt** (e.g. `precipitation_mm > 1`,
  `wind_speed_kmh > 25`) make property-based evals tractable: "given temp=40°F
  and rain=10mm, the recommendation must mention waterproof outerwear."
