"""Zillow-style terminal display for mortgage scenario results."""

from __future__ import annotations

from typing import Any


def _bar_segment(amount: float, total: float, width: int = 40) -> int:
    if total <= 0:
        return 0
    return max(1, round((amount / total) * width))


def format_zillow_style(result: dict[str, Any]) -> str:
    """Render estimated payment breakdown similar to Zillow's payment calculator."""
    scenario = result["scenario"]
    breakdown = scenario["monthly_breakdown"]
    total = breakdown["total_estimated_payment"]
    pi = breakdown["principal_interest"]
    tax = breakdown["property_taxes"]
    pmi = breakdown["pmi"]
    other = breakdown["home_insurance"] + breakdown["hoa"] + breakdown["utilities"] + pmi

    w = 36
    pi_w = _bar_segment(pi, total, w)
    tax_w = _bar_segment(tax, total, w)
    other_w = max(0, w - pi_w - tax_w)

    bar = "█" * pi_w + "▓" * tax_w + "░" * other_w

    lines = [
        "",
        "╔══════════════════════════════════════════════════════════════╗",
        "║           ESTIMATED MONTHLY PAYMENT (BuyAbility-style)       ║",
        "╠══════════════════════════════════════════════════════════════╣",
        f"║  ${total:>10,.0f}/mo                                          ║",
        "║                                                              ║",
        f"║  {bar}  ║",
        "║                                                              ║",
        f"║  ■ Principal & interest     ${pi:>10,.0f}/mo                   ║",
        f"║  ■ Property taxes           ${tax:>10,.0f}/mo                   ║",
        f"║  ■ Other (ins+HOA+util+PMI) ${other:>10,.0f}/mo                   ║",
        "╠══════════════════════════════════════════════════════════════╣",
        f"║  Purchase price   ${scenario['inputs']['purchase_price']:>12,.0f}              ║",
        f"║  Down payment     ${scenario['down_payment']:>12,.0f}              ║",
        f"║  Loan amount      ${scenario['loan_amount']:>12,.0f}              ║",
        f"║  Interest rate    {scenario['effective_annual_rate_percent']:>12.3f}%              ║",
        f"║  LTV              {scenario['ltv']['ltv_percent']:>12.1f}%              ║",
    ]

    aff = scenario.get("affordability")
    if aff:
        lines.extend(
            [
                "╠══════════════════════════════════════════════════════════════╣",
                f"║  Household income ${scenario['inputs']['annual_income']:>11,.0f}/yr              ║",
                f"║  Front-end DTI    {aff['front_end_dti_percent']:>12.1f}%              ║",
                f"║  Back-end DTI     {aff['back_end_dti_percent']:>12.1f}%              ║",
            ]
        )
    credit = scenario.get("credit_tier")
    if credit:
        lines.append(
            f"║  Credit tier      {credit['tier']:>12} (score {credit['credit_score']})   ║"
        )

    lines.extend(
        [
            "╠══════════════════════════════════════════════════════════════╣",
            "║  Payment breakdown detail                                    ║",
            f"║    Home insurance   ${breakdown['home_insurance']:>8,.0f}/mo                       ║",
            f"║    HOA              ${breakdown['hoa']:>8,.0f}/mo                       ║",
            f"║    Utilities        ${breakdown['utilities']:>8,.0f}/mo                       ║",
            f"║    PMI              ${breakdown['pmi']:>8,.0f}/mo                       ║",
            f"║    Cash to close    ${scenario['cash_to_close']['cash_to_close']:>8,.0f}                       ║",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
            scenario["disclaimer"],
            "",
        ]
    )
    return "\n".join(lines)
