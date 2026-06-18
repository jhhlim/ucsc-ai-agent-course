"""Mortgage calculation tools used by specialist agents and the compliance critic."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import requests

# Educational credit-tier rate adjustments (basis points over benchmark). No credit pull.
CREDIT_TIER_ADJUSTMENTS_BPS: dict[str, int] = {
    "760+": 0,
    "740-759": 12,
    "720-739": 25,
    "700-719": 50,
    "680-699": 87,
    "660-679": 125,
    "<660": 200,
}

CLOSING_COST_RATE = 0.03  # 3% of purchase price estimate
PMI_ANNUAL_RATE = 0.005  # 0.5% of loan amount when LTV > 80%


@dataclass
class ScenarioInputs:
    purchase_price: float
    annual_interest_rate: float
    loan_term_years: int = 30
    down_payment: float | None = None
    down_payment_percent: float | None = 20.0
    annual_income: float | None = None
    credit_score: int | None = None
    monthly_debts: float = 0.0
    monthly_property_tax: float = 0.0
    monthly_home_insurance: float = 0.0
    monthly_hoa: float = 0.0
    monthly_utilities: float = 0.0
    use_fred_rate: bool = False


def _resolve_down_payment(inputs: ScenarioInputs) -> float:
    if inputs.down_payment is not None:
        return inputs.down_payment
    pct = inputs.down_payment_percent if inputs.down_payment_percent is not None else 20.0
    return inputs.purchase_price * (pct / 100.0)


def get_mortgage_rates(series_id: str = "MORTGAGE30US") -> dict[str, Any]:
    """Fetch national 30-year fixed mortgage benchmarks via the FRED API.

    Args:
        series_id: FRED series id (default MORTGAGE30US).

    Returns:
        Dict with latest rate, observation date, and source disclaimer.
    """
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        return {
            "available": False,
            "error": "FRED_API_KEY not set; use user-supplied rate instead.",
            "disclaimer": "Benchmark rates unavailable without FRED_API_KEY.",
        }

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        observations = response.json().get("observations", [])
        for obs in observations:
            value = obs.get("value")
            if value and value != ".":
                return {
                    "available": True,
                    "series_id": series_id,
                    "rate_percent": float(value),
                    "observation_date": obs.get("date"),
                    "source": "FRED / Freddie Mac PMMS",
                    "disclaimer": (
                        "Published national benchmark; your offered rate may differ "
                        "based on credit, LTV, points, and lender."
                    ),
                }
        return {"available": False, "error": "No recent FRED observations found."}
    except requests.RequestException as exc:
        return {"available": False, "error": str(exc)}


def calculate_monthly_payment(
    loan_amount: float,
    annual_interest_rate: float,
    loan_term_years: int = 30,
) -> dict[str, float]:
    """Compute principal-and-interest payment from loan amount, rate, and term.

    Args:
        loan_amount: Principal borrowed.
        annual_interest_rate: Nominal annual rate as a percent (e.g. 6.0 for 6%).
        loan_term_years: Amortization term in years.

    Returns:
        Monthly P&I payment and total interest over the life of the loan.
    """
    if loan_amount <= 0:
        return {"monthly_principal_interest": 0.0, "total_interest": 0.0}
    if annual_interest_rate <= 0:
        monthly = loan_amount / (loan_term_years * 12)
        return {
            "monthly_principal_interest": round(monthly, 2),
            "total_interest": 0.0,
        }

    monthly_rate = annual_interest_rate / 100.0 / 12.0
    n_payments = loan_term_years * 12
    factor = (1 + monthly_rate) ** n_payments
    monthly_pi = loan_amount * monthly_rate * factor / (factor - 1)
    total_paid = monthly_pi * n_payments
    return {
        "monthly_principal_interest": round(monthly_pi, 2),
        "total_interest": round(total_paid - loan_amount, 2),
    }


def calculate_ltv(purchase_price: float, loan_amount: float) -> dict[str, Any]:
    """Compute loan-to-value and PMI threshold flags for conventional loans.

    Args:
        purchase_price: Home purchase price.
        loan_amount: Amount financed.

    Returns:
        LTV percent, down payment percent, and whether PMI likely applies.
    """
    if purchase_price <= 0:
        raise ValueError("purchase_price must be positive")
    ltv = (loan_amount / purchase_price) * 100.0
    down_pct = 100.0 - ltv
    return {
        "ltv_percent": round(ltv, 2),
        "down_payment_percent": round(down_pct, 2),
        "pmi_required": ltv > 80.0,
        "pmi_threshold_ltv": 80.0,
    }


def estimate_pmi(loan_amount: float, ltv_percent: float) -> dict[str, float]:
    """Estimate monthly PMI when LTV exceeds 80% on a conventional loan.

    Args:
        loan_amount: Principal borrowed.
        ltv_percent: Current loan-to-value ratio.

    Returns:
        Monthly PMI estimate (0 when LTV <= 80%).
    """
    if ltv_percent <= 80.0:
        return {"monthly_pmi": 0.0, "annual_pmi_rate_percent": 0.0}
    monthly = loan_amount * PMI_ANNUAL_RATE / 12.0
    return {
        "monthly_pmi": round(monthly, 2),
        "annual_pmi_rate_percent": PMI_ANNUAL_RATE * 100.0,
    }


def calculate_cash_to_close(
    purchase_price: float,
    down_payment: float,
    closing_cost_rate: float = CLOSING_COST_RATE,
) -> dict[str, float]:
    """Estimate cash needed at closing: down payment plus closing costs.

    Args:
        purchase_price: Home purchase price.
        down_payment: Cash down payment amount.
        closing_cost_rate: Closing costs as a fraction of purchase price.

    Returns:
        Down payment, estimated closing costs, and total cash to close.
    """
    closing_costs = purchase_price * closing_cost_rate
    return {
        "down_payment": round(down_payment, 2),
        "estimated_closing_costs": round(closing_costs, 2),
        "cash_to_close": round(down_payment + closing_costs, 2),
    }


def analyze_credit_tier(credit_score: int) -> dict[str, Any]:
    """Map a user-supplied FICO score to an educational rate tier (no credit pull).

    Args:
        credit_score: Self-reported FICO score.

    Returns:
        Tier label and illustrative rate adjustment in basis points.
    """
    if credit_score >= 760:
        tier = "760+"
    elif credit_score >= 740:
        tier = "740-759"
    elif credit_score >= 720:
        tier = "720-739"
    elif credit_score >= 700:
        tier = "700-719"
    elif credit_score >= 680:
        tier = "680-699"
    elif credit_score >= 660:
        tier = "660-679"
    else:
        tier = "<660"
    return {
        "credit_score": credit_score,
        "tier": tier,
        "rate_adjustment_bps": CREDIT_TIER_ADJUSTMENTS_BPS[tier],
        "disclaimer": "Educational tier only; not a credit pull or loan offer.",
    }


def score_income_affordability(
    gross_annual_income: float,
    monthly_housing_payment: float,
    monthly_debts: float = 0.0,
) -> dict[str, Any]:
    """Compute front-end and back-end debt-to-income ratios.

    Args:
        gross_annual_income: Pre-tax annual household income.
        monthly_housing_payment: Total proposed monthly housing cost (PITI+HOA+utilities).
        monthly_debts: Other monthly debt obligations (car, student loans, etc.).

    Returns:
        Monthly gross income, front-end DTI, back-end DTI, and guideline notes.
    """
    monthly_income = gross_annual_income / 12.0
    if monthly_income <= 0:
        raise ValueError("gross_annual_income must be positive")
    front_end = (monthly_housing_payment / monthly_income) * 100.0
    back_end = ((monthly_housing_payment + monthly_debts) / monthly_income) * 100.0
    return {
        "monthly_gross_income": round(monthly_income, 2),
        "monthly_housing_payment": round(monthly_housing_payment, 2),
        "monthly_debts": round(monthly_debts, 2),
        "front_end_dti_percent": round(front_end, 2),
        "back_end_dti_percent": round(back_end, 2),
        "conventional_guideline_note": (
            "Illustrative only: many lenders target ~28% front-end and ~36% back-end DTI "
            "for conventional loans; actual limits vary by program and compensating factors."
        ),
    }


def verify_calculations(
    loan_amount: float,
    annual_interest_rate: float,
    loan_term_years: int,
    reported_monthly_pi: float,
) -> dict[str, Any]:
    """Critic-only tool: re-run key formulas to catch arithmetic errors.

    Args:
        loan_amount: Principal borrowed.
        annual_interest_rate: Nominal annual rate as a percent (e.g. 6.0).
        loan_term_years: Amortization term in years.
        reported_monthly_pi: P&I amount reported by a specialist agent.

    Returns:
        Verification status and any mismatches found.
    """
    expected = calculate_monthly_payment(
        loan_amount=loan_amount,
        annual_interest_rate=annual_interest_rate,
        loan_term_years=loan_term_years,
    )
    reported = float(reported_monthly_pi)
    delta = abs(expected["monthly_principal_interest"] - reported)
    ok = delta < 1.0
    return {
        "payment_verified": ok,
        "expected_monthly_pi": expected["monthly_principal_interest"],
        "reported_monthly_pi": reported,
        "delta_dollars": round(delta, 2),
    }


def run_full_scenario(inputs: ScenarioInputs) -> dict[str, Any]:
    """Run all mortgage calculations for a single scenario (used by specialists)."""
    down_payment = _resolve_down_payment(inputs)
    loan_amount = inputs.purchase_price - down_payment
    ltv_info = calculate_ltv(inputs.purchase_price, loan_amount)
    pmi_info = estimate_pmi(loan_amount, ltv_info["ltv_percent"])

    effective_rate = inputs.annual_interest_rate
    fred = None
    if inputs.use_fred_rate:
        fred = get_mortgage_rates()
        if fred.get("available"):
            effective_rate = fred["rate_percent"]

    credit_info = None
    if inputs.credit_score is not None:
        credit_info = analyze_credit_tier(inputs.credit_score)
        effective_rate += credit_info["rate_adjustment_bps"] / 100.0

    payment_info = calculate_monthly_payment(
        loan_amount, effective_rate, inputs.loan_term_years
    )
    cash_info = calculate_cash_to_close(inputs.purchase_price, down_payment)

    monthly_pmi = pmi_info["monthly_pmi"]
    monthly_tax = inputs.monthly_property_tax
    monthly_insurance = inputs.monthly_home_insurance
    monthly_hoa = inputs.monthly_hoa
    monthly_utilities = inputs.monthly_utilities
    monthly_pi = payment_info["monthly_principal_interest"]

    monthly_escrow_and_other = monthly_tax + monthly_insurance + monthly_hoa + monthly_utilities
    total_monthly = monthly_pi + monthly_pmi + monthly_escrow_and_other

    affordability = None
    if inputs.annual_income:
        affordability = score_income_affordability(
            inputs.annual_income, total_monthly, inputs.monthly_debts
        )

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "inputs": asdict(inputs),
        "down_payment": round(down_payment, 2),
        "loan_amount": round(loan_amount, 2),
        "effective_annual_rate_percent": round(effective_rate, 3),
        "fred_benchmark": fred,
        "credit_tier": credit_info,
        "ltv": ltv_info,
        "payment": payment_info,
        "pmi": pmi_info,
        "cash_to_close": cash_info,
        "monthly_breakdown": {
            "principal_interest": monthly_pi,
            "pmi": monthly_pmi,
            "property_taxes": monthly_tax,
            "home_insurance": monthly_insurance,
            "hoa": monthly_hoa,
            "utilities": monthly_utilities,
            "other_costs_subtotal": round(monthly_escrow_and_other, 2),
            "total_estimated_payment": round(total_monthly, 2),
        },
        "affordability": affordability,
        "disclaimer": (
            "Educational estimate only — not financial advice, not a loan offer, "
            "and not an underwriting decision."
        ),
    }
