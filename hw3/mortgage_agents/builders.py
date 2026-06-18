"""Shared ADK agent definitions for mortgage multi-agent system."""

from __future__ import annotations

import sys
from pathlib import Path

_HW3_ROOT = Path(__file__).resolve().parent.parent
if str(_HW3_ROOT) not in sys.path:
    sys.path.insert(0, str(_HW3_ROOT))

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import FunctionTool

from mortgage_agents.model_config import get_doubleword_litellm, get_planner
from mortgage_agents.tools import (
    analyze_credit_tier,
    calculate_cash_to_close,
    calculate_ltv,
    calculate_monthly_payment,
    estimate_pmi,
    get_mortgage_rates,
    score_income_affordability,
    verify_calculations,
)

_model = get_doubleword_litellm()
_planner = get_planner()

rate_finder_agent = LlmAgent(
    name="rate_finder_agent",
    model=_model,
    planner=_planner,
    description="Fetches benchmark mortgage rates and explains loan structure.",
    instruction=(
        "You are the Rate Finder Agent. Use get_mortgage_rates to fetch the FRED "
        "MORTGAGE30US benchmark when asked. Explain fixed vs ARM and 15 vs 30 year "
        "tradeoffs factually. Never recommend a specific loan. Write a concise report."
    ),
    tools=[FunctionTool(get_mortgage_rates)],
    output_key="rate_report",
)

payment_calculator_agent = LlmAgent(
    name="payment_calculator_agent",
    model=_model,
    planner=_planner,
    description="Calculates LTV, monthly P&I, PMI, and cash to close.",
    instruction=(
        "You are the LTV / Payment Calculator Agent. Use calculate_ltv, "
        "calculate_monthly_payment, estimate_pmi, and calculate_cash_to_close. "
        "Include property tax, insurance, HOA, and utilities when the user provides them. "
        "Present numbers clearly. Do not give advice."
    ),
    tools=[
        FunctionTool(calculate_monthly_payment),
        FunctionTool(calculate_ltv),
        FunctionTool(estimate_pmi),
        FunctionTool(calculate_cash_to_close),
    ],
    output_key="payment_report",
)

affordability_analyzer_agent = LlmAgent(
    name="affordability_analyzer_agent",
    model=_model,
    planner=_planner,
    description="Maps credit score to tier and computes DTI ratios.",
    instruction=(
        "You are the Credit / Affordability Analyzer Agent. Use analyze_credit_tier "
        "and score_income_affordability. Explain front-end and back-end DTI as "
        "illustrative metrics only — not underwriting decisions."
    ),
    tools=[
        FunctionTool(analyze_credit_tier),
        FunctionTool(score_income_affordability),
    ],
    output_key="affordability_report",
)

_specialists = ParallelAgent(
    name="mortgage_specialists",
    description="Runs rate, payment, and affordability specialists in parallel.",
    sub_agents=[rate_finder_agent, payment_calculator_agent, affordability_analyzer_agent],
)

synthesizer_agent = LlmAgent(
    name="scenario_synthesizer",
    model=_model,
    planner=_planner,
    description="Combines specialist outputs into a structured scenario summary.",
    instruction=(
        "Synthesize the mortgage scenario using specialist reports:\n"
        "Rate: {rate_report?}\n"
        "Payment: {payment_report?}\n"
        "Affordability: {affordability_report?}\n\n"
        "Present side-by-side numbers, tradeoffs, and explanations. "
        "Do NOT use advice language (no 'you should', 'you can afford', 'I recommend'). "
        "End with an educational disclaimer."
    ),
    output_key="draft_response",
)

compliance_critic_agent = LlmAgent(
    name="compliance_critic_agent",
    model=_model,
    planner=_planner,
    description="Reviews draft for math errors and advice-giving language.",
    instruction=(
        "You are the Compliance Critic. Review this draft:\n{draft_response?}\n\n"
        "Use verify_calculations with loan_amount, annual_interest_rate, "
        "loan_term_years, and reported_monthly_pi when loan numbers are present. "
        "Flag arithmetic errors, missing disclaimers, and advice language. "
        "If issues exist, output REVISE: followed by corrected text. "
        "If clean, output APPROVED: followed by the final text."
    ),
    tools=[FunctionTool(verify_calculations)],
    output_key="critic_review",
)

_finalizer_agent = LlmAgent(
    name="response_finalizer",
    model=_model,
    planner=_planner,
    description="Produces the final user-facing response after critic review.",
    instruction=(
        "Using the critic review:\n{critic_review?}\n\n"
        "If REVISE was requested, apply fixes. Return the final educational summary "
        "with disclaimer. Never recommend a specific loan choice."
    ),
    output_key="final_response",
)

supervisor_agent = SequentialAgent(
    name="mortgage_supervisor",
    description=(
        "Full pipeline: parallel specialists → synthesizer → compliance critic → finalizer."
    ),
    sub_agents=[_specialists, synthesizer_agent, compliance_critic_agent, _finalizer_agent],
)

# Back-compat alias used by adk run on the legacy agents/ path
root_agent = supervisor_agent
