"""CLI runner for the Zillow-style mortgage scenario calculator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HW3 = Path(__file__).resolve().parent
if str(_HW3) not in sys.path:
    sys.path.insert(0, str(_HW3))

from mortgage_agents.display import format_zillow_style
from mortgage_agents.orchestrator import MortgageOrchestrator
from mortgage_agents.tools import ScenarioInputs


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Multi-agent conventional mortgage scenario calculator (HW3)"
    )
    p.add_argument("--purchase-price", type=float, default=1_280_000)
    p.add_argument("--interest-rate", type=float, default=6.0, help="Annual rate %%")
    p.add_argument("--down-payment", type=float, default=None)
    p.add_argument("--down-percent", type=float, default=20.0)
    p.add_argument("--term-years", type=int, default=30)
    p.add_argument("--annual-income", type=float, default=190_000)
    p.add_argument("--credit-score", type=int, default=770)
    p.add_argument("--monthly-debts", type=float, default=0.0)
    p.add_argument("--property-tax", type=float, default=1_300)
    p.add_argument("--home-insurance", type=float, default=150)
    p.add_argument("--hoa", type=float, default=25)
    p.add_argument("--utilities", type=float, default=300)
    p.add_argument("--use-fred", action="store_true", help="Use live FRED benchmark rate")
    p.add_argument("--json", action="store_true", help="Print full JSON result")
    p.add_argument("--no-narrative", action="store_true", help="Skip agent narratives")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = ScenarioInputs(
        purchase_price=args.purchase_price,
        annual_interest_rate=args.interest_rate,
        loan_term_years=args.term_years,
        down_payment=args.down_payment,
        down_payment_percent=args.down_percent,
        annual_income=args.annual_income,
        credit_score=args.credit_score,
        monthly_debts=args.monthly_debts,
        monthly_property_tax=args.property_tax,
        monthly_home_insurance=args.home_insurance,
        monthly_hoa=args.hoa,
        monthly_utilities=args.utilities,
        use_fred_rate=args.use_fred,
    )

    result = MortgageOrchestrator().run_scenario(inputs)

    print(format_zillow_style(result))

    if not args.no_narrative:
        print("── Agent narratives ──")
        for name, text in result["specialist_narratives"].items():
            print(f"\n[{name}]\n{text}")

        critic = result["critic_log"][-1] if result["critic_log"] else {}
        status = "APPROVED" if critic.get("approved") else "REVISED"
        print(f"\n[Compliance Critic] {status}")
        if critic.get("issues"):
            for issue in critic["issues"]:
                print(f"  - {issue}")

    if args.json:
        print("\n── Full JSON ──")
        print(json.dumps(result, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
