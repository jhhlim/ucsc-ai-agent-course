#!/usr/bin/env python3
"""Capture LangSmith project / experiment / trace screenshots after eval."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HW3 = Path(__file__).resolve().parent
_SHOTS = _HW3 / "langsmith_screenshots"
_ORG = "0e0ab241-41c6-425d-afbb-dbeafa0df253"
_BASE = f"https://smith.langchain.com/o/{_ORG}"


def _load_meta() -> dict:
    path = _HW3 / "langsmith_eval_results.json"
    if path.is_file():
        return json.loads(path.read_text())
    return {}


def _urls(meta: dict) -> list[tuple[str, str]]:
    exp_project = meta.get("experiment_project", "hw3-mortgage-orchestrator-1de98a4c")
    urls = [
        ("02_projects_list", f"{_BASE}/projects"),
        ("03_experiment_traces", f"{_BASE}/projects/p/{exp_project}"),
    ]
    if meta.get("compare_url"):
        urls.append(("04_experiment_compare", meta["compare_url"]))
    return urls


def capture_with_playwright(urls: list[tuple[str, str]]) -> list[str]:
    from playwright.sync_api import sync_playwright

    saved: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, url in urls:
            page.goto(url, wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(3000)
            path = _SHOTS / f"{name}.png"
            page.screenshot(path=str(path), full_page=True)
            saved.append(str(path))
            print(f"Saved {path}")
        browser.close()
    return saved


def capture_trace_detail_from_api(meta: dict) -> str | None:
    from langsmith import Client
    from playwright.sync_api import sync_playwright

    project = meta.get("experiment_project", "hw3-mortgage-orchestrator-1de98a4c")
    client = Client()
    runs = list(client.list_runs(project_name=project, is_root=True, limit=3))
    if not runs:
        return None

    run = runs[0]
    trace_url = f"{_BASE}/projects/p/{project}/r/{run.id}"
    children = list(client.list_runs(project_name=project, trace_id=run.trace_id, limit=20))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(trace_url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(4000)
        path = _SHOTS / "05_trace_detail.png"
        page.screenshot(path=str(path), full_page=True)
        browser.close()

    (_SHOTS / "trace_meta.json").write_text(
        json.dumps(
            {
                "root_run_id": str(run.id),
                "trace_id": str(run.trace_id),
                "trace_url": trace_url,
                "child_runs": len(children),
                "run_name": run.name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved {_SHOTS / '05_trace_detail.png'}")
    return trace_url


def main() -> None:
    sys.path.insert(0, str(_HW3))
    from mortgage_agents.langsmith_tracing import configure_langsmith_tracing

    configure_langsmith_tracing()
    _SHOTS.mkdir(parents=True, exist_ok=True)
    meta = _load_meta()
    capture_with_playwright(_urls(meta))
    capture_trace_detail_from_api(meta)


if __name__ == "__main__":
    main()
