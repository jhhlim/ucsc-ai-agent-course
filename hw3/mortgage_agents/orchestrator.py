"""Supervisor + specialist workers + compliance critic orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mortgage_agents.tools import (
    ScenarioInputs,
    analyze_credit_tier,
    calculate_cash_to_close,
    calculate_ltv,
    calculate_monthly_payment,
    estimate_pmi,
    get_mortgage_rates,
    run_full_scenario,
    score_income_affordability,
    verify_calculations,
)

ADVICE_PATTERNS = [
    r"\byou should\b",
    r"\byou must\b",
    r"\bi recommend\b",
    r"\bwe recommend\b",
    r"\byou can afford\b",
    r"\byou cannot afford\b",
    r"\btake this loan\b",
    r"\bgo with\b",
    r"\bbest (choice|option|loan)\b",
]


@dataclass
class AgentReport:
    agent_name: str
    output_key: str
    payload: dict[str, Any]
    narrative: str


def _rate_finder_worker(inputs: ScenarioInputs) -> AgentReport:
    fred = get_mortgage_rates()
    benchmark = fred.get("rate_percent") if fred.get("available") else None
    payload = {
        "user_rate_percent": inputs.annual_interest_rate,
        "fred_benchmark": fred,
        "loan_term_years": inputs.loan_term_years,
        "structure": "30-year fixed conventional (illustrative)",
    }
    if benchmark is not None:
        narrative = (
            f"National 30-year fixed benchmark (FRED MORTGAGE30US): {benchmark:.2f}% "
            f"as of {fred.get('observation_date')}. "
            f"Your scenario uses {inputs.annual_interest_rate:.2f}% as supplied."
        )
    else:
        narrative = (
            f"Scenario uses a user-supplied {inputs.annual_interest_rate:.2f}% rate "
            f"on a {inputs.loan_term_years}-year fixed conventional structure. "
            f"Live FRED benchmark unavailable ({fred.get('error', 'no key')})."
        )
    return AgentReport("Rate Finder Agent", "rate_report", payload, narrative)


def _payment_calculator_worker(inputs: ScenarioInputs) -> AgentReport:
    down = inputs.down_payment
    if down is None:
        pct = inputs.down_payment_percent or 20.0
        down = inputs.purchase_price * (pct / 100.0)
    loan = inputs.purchase_price - down
    ltv = calculate_ltv(inputs.purchase_price, loan)
    pmi = estimate_pmi(loan, ltv["ltv_percent"])
    payment = calculate_monthly_payment(loan, inputs.annual_interest_rate, inputs.loan_term_years)
    cash = calculate_cash_to_close(inputs.purchase_price, down)
    monthly_other = (
        inputs.monthly_property_tax
        + inputs.monthly_home_insurance
        + inputs.monthly_hoa
        + inputs.monthly_utilities
        + pmi["monthly_pmi"]
    )
    total = payment["monthly_principal_interest"] + monthly_other
    payload = {
        "purchase_price": inputs.purchase_price,
        "down_payment": round(down, 2),
        "loan_amount": round(loan, 2),
        "ltv": ltv,
        "pmi": pmi,
        "payment": payment,
        "cash_to_close": cash,
        "monthly_other_costs": round(monthly_other, 2),
        "total_monthly_payment": round(total, 2),
        "monthly_breakdown": {
            "principal_interest": payment["monthly_principal_interest"],
            "property_taxes": inputs.monthly_property_tax,
            "home_insurance": inputs.monthly_home_insurance,
            "hoa": inputs.monthly_hoa,
            "utilities": inputs.monthly_utilities,
            "pmi": pmi["monthly_pmi"],
        },
    }
    narrative = (
        f"On ${inputs.purchase_price:,.0f} with ${down:,.0f} down ({ltv['down_payment_percent']:.1f}%), "
        f"loan amount is ${loan:,.0f} (LTV {ltv['ltv_percent']:.1f}%). "
        f"Principal & interest: ${payment['monthly_principal_interest']:,.2f}/mo. "
        f"PMI: ${pmi['monthly_pmi']:,.2f}/mo. "
        f"Taxes, insurance, HOA, utilities: ${monthly_other - pmi['monthly_pmi']:,.2f}/mo. "
        f"Estimated total monthly: ${total:,.2f}/mo. "
        f"Cash to close (incl. ~3% closing costs): ${cash['cash_to_close']:,.0f}."
    )
    return AgentReport("LTV / Payment Calculator Agent", "payment_report", payload, narrative)


def _affordability_worker(inputs: ScenarioInputs) -> AgentReport:
    full = run_full_scenario(inputs)
    total = full["monthly_breakdown"]["total_estimated_payment"]
    credit = analyze_credit_tier(inputs.credit_score) if inputs.credit_score else None
    affordability = None
    if inputs.annual_income:
        affordability = score_income_affordability(
            inputs.annual_income, total, inputs.monthly_debts
        )
    payload = {
        "annual_income": inputs.annual_income,
        "credit_tier": credit,
        "affordability": affordability,
        "total_monthly_housing": total,
    }
    if affordability and credit:
        narrative = (
            f"With ${inputs.annual_income:,.0f} gross annual income, estimated housing payment "
            f"${total:,.2f}/mo yields front-end DTI {affordability['front_end_dti_percent']:.1f}% "
            f"and back-end DTI {affordability['back_end_dti_percent']:.1f}% "
            f"(other debts ${inputs.monthly_debts:,.0f}/mo). "
            f"Credit score {inputs.credit_score} maps to tier '{credit['tier']}' "
            f"(educational rate adjustment +{credit['rate_adjustment_bps']} bps vs benchmark)."
        )
    elif affordability:
        narrative = (
            f"Front-end DTI {affordability['front_end_dti_percent']:.1f}%, "
            f"back-end DTI {affordability['back_end_dti_percent']:.1f}% "
            f"at ${total:,.2f}/mo housing."
        )
    else:
        narrative = "Income not provided; DTI metrics skipped."
    return AgentReport(
        "Credit / Affordability Analyzer Agent", "affordability_report", payload, narrative
    )


def _compliance_critic(
    synthesis: str,
    payment_payload: dict[str, Any],
    inputs: ScenarioInputs,
    iteration: int,
) -> dict[str, Any]:
    verify_input = {
        "loan_amount": payment_payload["loan_amount"],
        "annual_interest_rate": inputs.annual_interest_rate,
        "loan_term_years": inputs.loan_term_years,
        "reported_monthly_pi": payment_payload["payment"]["monthly_principal_interest"],
    }
    math_check = verify_calculations(**verify_input)
    advice_hits = [
        pat for pat in ADVICE_PATTERNS if re.search(pat, synthesis, re.IGNORECASE)
    ]
    has_disclaimer = "not financial advice" in synthesis.lower() or "educational" in synthesis.lower()
    issues: list[str] = []
    if not math_check["payment_verified"]:
        issues.append(
            f"P&I mismatch: expected ${math_check['expected_monthly_pi']:,.2f}, "
            f"reported ${math_check['reported_monthly_pi']:,.2f}."
        )
    if advice_hits:
        issues.append(f"Advice-like language detected: {advice_hits}")
    if not has_disclaimer:
        issues.append("Missing educational / not-advice disclaimer.")
    if payment_payload["ltv"]["pmi_required"] and payment_payload["pmi"]["monthly_pmi"] == 0:
        issues.append("LTV > 80% but PMI shown as $0.")

    return {
        "iteration": iteration,
        "approved": len(issues) == 0,
        "issues": issues,
        "math_check": math_check,
        "advice_patterns_matched": advice_hits,
    }


def _synthesize_reports(
    rate: AgentReport, payment: AgentReport, affordability: AgentReport
) -> str:
    lines = [
        "## Multi-Agent Mortgage Scenario Summary",
        "",
        "### Rate Finder",
        rate.narrative,
        "",
        "### Payment & LTV",
        payment.narrative,
        "",
        "### Affordability & Credit",
        affordability.narrative,
        "",
        "### Tradeoffs (informational)",
        "- Higher down payment lowers LTV, may eliminate PMI, and reduces monthly P&I.",
        "- Lower down payment preserves cash but increases loan balance and may add PMI.",
        "- Property taxes, insurance, HOA, and utilities add to total monthly cost beyond P&I.",
        "",
        "_Educational estimate only — not financial advice, not a loan offer, "
        "and not an underwriting decision._",
    ]
    return "\n".join(lines)


def _revise_synthesis(synthesis: str, issues: list[str]) -> str:
    revised = synthesis
    for issue in issues:
        if "Advice-like" in issue:
            revised = re.sub(
                r"\byou should\b", "one option to consider is", revised, flags=re.IGNORECASE
            )
            revised = re.sub(
                r"\byou can afford\b", "DTI metrics suggest", revised, flags=re.IGNORECASE
            )
    if "not financial advice" not in revised.lower():
        revised += (
            "\n\n_Educational estimate only — not financial advice, not a loan offer, "
            "and not an underwriting decision._"
        )
    return revised


class MortgageOrchestrator:
    """Supervisor that routes to parallel specialists, then runs the compliance critic."""

    def run_scenario(self, inputs: ScenarioInputs, max_critic_iterations: int = 2) -> dict[str, Any]:
        # Supervisor: full scenario always runs all three specialists in parallel
        rate_report = _rate_finder_worker(inputs)
        payment_report = _payment_calculator_worker(inputs)
        affordability_report = _affordability_worker(inputs)

        synthesis = _synthesize_reports(rate_report, payment_report, affordability_report)
        critic_log: list[dict[str, Any]] = []

        for iteration in range(1, max_critic_iterations + 1):
            review = _compliance_critic(
                synthesis,
                payment_report.payload,
                inputs,
                iteration,
            )
            critic_log.append(review)
            if review["approved"]:
                break
            synthesis = _revise_synthesis(synthesis, review["issues"])

        full = run_full_scenario(inputs)
        return {
            "orchestration": "Supervisor → ParallelAgent(rate, payment, affordability) → Critic",
            "specialist_reports": {
                rate_report.output_key: rate_report.payload,
                payment_report.output_key: payment_report.payload,
                affordability_report.output_key: affordability_report.payload,
            },
            "specialist_narratives": {
                rate_report.agent_name: rate_report.narrative,
                payment_report.agent_name: payment_report.narrative,
                affordability_report.agent_name: affordability_report.narrative,
            },
            "synthesis": synthesis,
            "critic_log": critic_log,
            "scenario": full,
        }
