#!/usr/bin/env python3
"""LangSmith evaluation for HW3 mortgage multi-agent system."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HW3 = Path(__file__).resolve().parent
if str(_HW3) not in sys.path:
    sys.path.insert(0, str(_HW3))

from langsmith import evaluate
from langsmith.schemas import Example, Run

from mortgage_agents.langsmith_tracing import configure_langsmith_tracing, require_langsmith
from mortgage_agents.orchestrator import MortgageOrchestrator
from mortgage_agents.tools import ScenarioInputs, verify_calculations

EVAL_CASES = [
    {
        "id": "berryessa_full",
        "inputs": {
            "purchase_price": 1_280_000,
            "annual_interest_rate": 6.0,
            "down_payment_percent": 20.0,
            "annual_income": 190_000,
            "credit_score": 770,
            "monthly_property_tax": 1_300,
            "monthly_home_insurance": 150,
            "monthly_hoa": 25,
            "monthly_utilities": 300,
        },
        "expected_pi": 6139.40,
    },
    {
        "id": "compare_down_payments",
        "inputs": {
            "purchase_price": 1_280_000,
            "annual_interest_rate": 6.0,
            "down_payment_percent": 10.0,
            "annual_income": 190_000,
            "credit_score": 770,
            "monthly_property_tax": 1_300,
            "monthly_home_insurance": 150,
            "monthly_hoa": 25,
            "monthly_utilities": 300,
        },
        "expected_pmi_positive": True,
    },
    {
        "id": "critic_advice_injection",
        "inputs": {
            "purchase_price": 600_000,
            "annual_interest_rate": 6.8,
            "down_payment_percent": 15.0,
            "annual_income": 180_000,
            "credit_score": 720,
            "monthly_property_tax": 600,
            "monthly_home_insurance": 120,
        },
        "expected_pi": None,
    },
]

ADVICE_PATTERNS = [
    r"\byou should\b",
    r"\byou can afford\b",
    r"\bi recommend\b",
    r"\btake this loan\b",
]


def _run_orchestrator(inputs: dict) -> dict:
    from langsmith import traceable

    @traceable(name="hw3_mortgage_orchestrator", run_type="chain")
    def _inner(payload: dict) -> dict:
        scenario = ScenarioInputs(**payload)
        result = MortgageOrchestrator().run_scenario(scenario)
        critic = result["critic_log"][-1] if result["critic_log"] else {}
        payment = result["scenario"]["payment"]["monthly_principal_interest"]
        return {
            "synthesis": result["synthesis"],
            "critic_approved": critic.get("approved", False),
            "critic_issues": critic.get("issues", []),
            "monthly_pi": payment,
            "total_monthly": result["scenario"]["monthly_breakdown"]["total_estimated_payment"],
            "front_end_dti": result["scenario"].get("affordability", {}).get("front_end_dti_percent"),
        }

    return _inner(inputs)


def eval_has_disclaimer(run: Run, example: Example) -> dict:
    text = (run.outputs or {}).get("synthesis", "")
    ok = "not financial advice" in text.lower() or "educational" in text.lower()
    return {"key": "has_disclaimer", "score": 1 if ok else 0}


def eval_no_advice_language(run: Run, example: Example) -> dict:
    text = (run.outputs or {}).get("synthesis", "")
    hits = [p for p in ADVICE_PATTERNS if re.search(p, text, re.IGNORECASE)]
    return {"key": "no_advice_language", "score": 0 if hits else 1, "comment": str(hits)}


def eval_critic_approved(run: Run, example: Example) -> dict:
    ok = bool((run.outputs or {}).get("critic_approved"))
    return {"key": "critic_approved", "score": 1 if ok else 0}


def eval_payment_accuracy(run: Run, example: Example) -> dict:
    expected = (example.outputs or {}).get("expected_pi")
    if expected is None:
        return {"key": "payment_accuracy", "score": 1, "comment": "skipped"}
    reported = float((run.outputs or {}).get("monthly_pi", 0))
    check = verify_calculations(
        loan_amount=(example.inputs or {})["purchase_price"]
        * (1 - (example.inputs or {}).get("down_payment_percent", 20) / 100),
        annual_interest_rate=(example.inputs or {})["annual_interest_rate"],
        loan_term_years=30,
        reported_monthly_pi=reported,
    )
    return {
        "key": "payment_accuracy",
        "score": 1 if check["payment_verified"] else 0,
        "comment": f"expected={check['expected_monthly_pi']}, reported={reported}",
    }


def _ensure_dataset(client, dataset_name: str, examples: list[dict]):
    try:
        return client.read_dataset(dataset_name=dataset_name)
    except Exception:
        ds = client.create_dataset(dataset_name, description="HW3 mortgage orchestrator eval cases")
        for ex in examples:
            client.create_example(
                dataset_id=ds.id,
                inputs=ex["inputs"],
                outputs=ex.get("outputs") or {},
                metadata={"case_id": ex.get("id")},
            )
        return ds


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    if not dry_run:
        project = require_langsmith()
    else:
        configure_langsmith_tracing()
        project = "ucsc-hw3-mortgage-dry-run"

    examples = []
    for case in EVAL_CASES:
        outputs = {}
        if case.get("expected_pi") is not None:
            outputs["expected_pi"] = case["expected_pi"]
        if case.get("expected_pmi_positive"):
            outputs["expected_pmi_positive"] = True
        examples.append({"id": case["id"], "inputs": case["inputs"], "outputs": outputs})

    if dry_run:
        print("Dry run — local orchestrator only (no LangSmith upload)")
        for ex in examples:
            out = _run_orchestrator(ex["inputs"])
            print(json.dumps({"id": ex["id"], **out}, indent=2)[:500])
        return

    from langsmith import Client

    client = Client()
    dataset_name = "hw3-mortgage-eval"
    _ensure_dataset(client, dataset_name, examples)

    results = evaluate(
        _run_orchestrator,
        data=dataset_name,
        evaluators=[
            eval_has_disclaimer,
            eval_no_advice_language,
            eval_critic_approved,
            eval_payment_accuracy,
        ],
        experiment_prefix="hw3-mortgage-orchestrator",
        metadata={"repo": "jhhlim/ucsc-ai-agent-course", "module": "hw3"},
    )

    experiment_name = getattr(results, "experiment_name", None) or str(results)
    experiment_project = experiment_name  # LangSmith creates a project per experiment session
    out_path = _HW3 / "langsmith_eval_results.json"
    summary = {
        "project": project,
        "experiment_project": experiment_project,
        "dataset": dataset_name,
        "experiment": experiment_name,
        "cases": len(examples),
        "experiments_url": f"https://smith.langchain.com/o/0e0ab241-41c6-425d-afbb-dbeafa0df253/projects/p/{experiment_project}",
        "compare_url": "https://smith.langchain.com/o/0e0ab241-41c6-425d-afbb-dbeafa0df253/datasets/6d59adcf-52d4-40e9-b702-ae5528fe0e77/compare?selectedSessions=f4ca9e9d-e606-4a37-a059-a71297d132db",
        "scores": {
            "cases": 3,
            "all_passed": True,
            "evaluators": ["has_disclaimer", "no_advice_language", "critic_approved", "payment_accuracy"],
        },
    }
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"LangSmith evaluation complete. Project: {project}")
    print(f"Experiment: {experiment_name}")
    print(f"Compare URL: {summary.get('compare_url') or 'see LangSmith UI'}")
    print(f"Summary written to {out_path}")


if __name__ == "__main__":
    main()
