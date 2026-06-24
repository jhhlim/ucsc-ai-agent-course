# **Jason Lim**

**UCSC AI Agent Applications**  
**Final Project Learnings — HW3**

**June 30th, 2026**

# **Learnings**

## **GitHub Repository**

https://github.com/jhhlim/ucsc-ai-agent-course/tree/main/hw3

**Key deliverables**

| Artifact | Description |
|----------|-------------|
| [`hw3/README.md`](README.md) | Setup, CLI + Web ADK run instructions, sample prompts |
| [`UCSCAIAgent_Mortgage_Finance_Proposal_2NEW.docx`](UCSCAIAgent_Mortgage_Finance_Proposal_2NEW.docx) | Project proposal |
| [`HW3_Sample_Prompt_Outputs.md`](HW3_Sample_Prompt_Outputs.md) | CLI (`adk run`) terminal screenshots |
| [`HW3_Web_ADK_Sample_Outputs.md`](HW3_Web_ADK_Sample_Outputs.md) | Web (`adk web`) Dev UI screenshots |
| [`langsmith_eval.py`](langsmith_eval.py) | LangSmith evaluation suite |
| [`run_scenario.py`](run_scenario.py) | Instant deterministic calculator (no LLM) |

---

## **What We Built**

### Multi-agent architecture (proposal pattern)

**Supervisor → Parallel specialists → Synthesizer → Compliance Critic → Finalizer**

| Agent | Role |
|-------|------|
| Rate Finder | FRED benchmark rates, loan structure tradeoffs |
| LTV / Payment Calculator | P&I, LTV, PMI, cash to close |
| Credit / Affordability Analyzer | Credit tier mapping, front/back-end DTI |
| Compliance Critic | Math verification (`verify_calculations`), advice-language filter |
| Response Finalizer | Applies critic feedback before user sees output |

Implemented in two layers:

1. **Google ADK + Doubleword (LiteLLM)** — `hw3/adk_agents/` for `adk run` and `adk web`
2. **Python orchestrator** — `mortgage_agents/orchestrator.py` for fast deterministic runs + critic loop (up to 2 revision passes)

### Reference scenario

Berryessa (San Jose) home — **$1.28M**, **6%** 30-year fixed, **20% down**, **$190k** income, **770** credit, tax **$1,300/mo**, insurance **$150**, HOA **$25**, utilities **$300**.

**Expected:** ~$6,139/mo P&I, ~$7,914/mo total, 80% LTV (no PMI), ~50% front-end DTI.

### Compliance Critic pattern — confirmed working

- **ADK pipeline:** critic runs after synthesizer; uses `verify_calculations` tool; outputs `APPROVED:` or `REVISE:`
- **Python orchestrator:** regex scan for advice language (`"you should"`, `"you can afford"`, etc.), disclaimer check, PMI/LTV consistency, P&I math re-run
- **Demo:** compliance_critic sample prompt caught *"You should take this loan — you can afford it"* and rewrote with educational disclaimer only

---

## **Interesting Observations**

* Multi-agent architectures produced more structured responses than a single-agent implementation.
* The Compliance Critic was effective at identifying recommendation-style language that appeared acceptable during initial testing.
* Agent orchestration and context passing required more effort than implementing the mortgage calculations themselves.
* **ADK Web UI** was better for demos (Events panel shows tool calls per specialist); **CLI** was better for quick iteration.
* **Deterministic `run_scenario.py`** matched LLM tool outputs on P&I math — calculations are reliable; language review varies by run.
* Web UI required pointing `adk web` at `hw3/adk_agents/` (not nested `agents/`) so each specialist appears in the dropdown.

---

## **Surprising Findings**

* Most system errors occurred between agents rather than within the individual calculation tools (e.g. import path for `adk web`, `verify_calculations` JSON vs structured params).
* The Critic Agent frequently caught issues that were overlooked by the specialized agents.
* Mortgage calculations were deterministic and reliable, while language-based review tasks showed more variability across runs.
* Full `mortgage_supervisor` pipeline takes **30–60+ seconds** per request (5 LLM stages + parallel specialists) — latency is the main UX cost.
* Doubleword model occasionally mis-parsed dollar amounts in short prompts (e.g. "$600k" → $100k) unless inputs were explicit.

---

## **Challenges Encountered**

* Designing clear responsibilities for each agent without overlapping functionality.
* Managing latency caused by multiple sequential LLM calls.
* Ensuring the Critic Agent received enough context to validate calculations and compliance language.
* **ADK web freeze** — fixed by correcting Python path bootstrap and using `hw3/adk_agents/` layout.
* **Screenshot automation** — Playwright capture of web UI Events panel; waiting for final response text required longer timeouts on supervisor runs.

---

## **LangSmith Tracing & Evaluation**

**Project URL:** https://smith.langchain.com/o/0e0ab241-41c6-425d-afbb-dbeafa0df253/projects

We added LangSmith integration for observability and automated scoring:

| File | Purpose |
|------|---------|
| `mortgage_agents/langsmith_tracing.py` | Enables `LANGSMITH_TRACING` + LiteLLM `langsmith` callback |
| `langsmith_eval.py` | Dataset-driven eval with 4 scorers |

### Evaluators

| Scorer | What it checks |
|--------|----------------|
| `has_disclaimer` | Response includes educational / not-advice disclaimer |
| `no_advice_language` | No `"you should"`, `"you can afford"`, etc. |
| `critic_approved` | Python critic loop approved synthesis |
| `payment_accuracy` | P&I within $1 of `verify_calculations` |

### Setup (required for live traces)

Add to `src/.env`:

```bash
LANGSMITH_API_KEY="lsv2_..."          # Settings → API Keys in LangSmith
LANGSMITH_PROJECT="ucsc-hw3-mortgage"
LANGSMITH_TRACING=true
```

Run evaluation:

```bash
cd src
uv run --with langsmith python ../hw3/langsmith_eval.py          # upload traces + scores
uv run --with langsmith python ../hw3/langsmith_eval.py --dry-run  # local only
```

ADK / Doubleword LLM calls are traced automatically via LiteLLM callback when the API key is set.

### LangSmith status

![LangSmith login required](langsmith_screenshots/01_langsmith_login.png)

*Screenshot: LangSmith requires login to view traces. An API key from your account is needed to upload runs from this repo — we could not complete live trace screenshots without your `LANGSMITH_API_KEY`.*

**To finish LangSmith screenshots:** sign in at the project URL above, create API key, add to `src/.env`, re-run `langsmith_eval.py`, then capture Traces / Experiments views in the UI.

---

## **What I Would Do Differently**

* Add persistent memory to compare mortgage scenarios across sessions.
* Experiment with Gemini 2.5 Pro and compare reasoning quality against Doubleword.
* ~~Build an automated evaluation suite with additional mortgage scenarios and scoring metrics.~~ → **Started with LangSmith evaluators**; extend with LLM-as-judge and more scenarios.
* Add real-world property tax and insurance lookups using external APIs.
* Add ADK `LoopAgent` for multi-pass critic revision in the LLM pipeline (currently one critic pass + finalizer).
* Pre-compute tool results for supervisor demos to reduce latency while keeping critic for language review.

---

## **Key Takeaway**

Building a multi-agent system highlighted that agent coordination, validation, and evaluation are often more challenging than the individual tools themselves. The Compliance Critic pattern significantly improved reliability by acting as a final verification layer before presenting results to the user. LangSmith provides the next layer — trace visibility and repeatable eval scores — once connected with an API key.

---

## **Quick commands**

```bash
# Instant math (no LLM)
cd src && uv run python ../hw3/run_scenario.py

# ADK CLI
cd src && uv run adk run ../hw3/adk_agents/mortgage_supervisor

# ADK Web UI
cd src && uv run adk web ../hw3/adk_agents --port 8000

# LangSmith eval
cd src && uv run --with langsmith python ../hw3/langsmith_eval.py
```
