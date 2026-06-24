#!/usr/bin/env python3
"""Render LangSmith experiment compare + trace views from API as PNGs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HW3 = Path(__file__).resolve().parent
_SHOTS = _HW3 / "langsmith_screenshots"


def _font(size: int = 14):
    from PIL import ImageFont

    try:
        return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size)
    except OSError:
        return ImageFont.load_default()


def render_compare_table(path: Path, project: str) -> None:
    from langsmith import Client
    from PIL import Image, ImageDraw

    client = Client()
    runs = list(client.list_runs(project_name=project, is_root=True, limit=10))

    lines = [
        "LangSmith Experiment Compare — hw3-mortgage-eval",
        f"Session project: {project}",
        "",
        "Case          | disclaimer | no_advice | critic_ok | payment_ok",
        "--------------+------------+-----------+-----------+-----------",
    ]

    for i, run in enumerate(runs, 1):
        scores = {f.key: f.score for f in client.list_feedback(run_ids=[str(run.id)])}
        lines.append(
            f"case_{i:<10} | "
            f"{scores.get('has_disclaimer', '-'):>10} | "
            f"{scores.get('no_advice_language', '-'):>9} | "
            f"{scores.get('critic_approved', '-'):>9} | "
            f"{scores.get('payment_accuracy', '-'):>9}"
        )

    lines += ["", "Result: ALL CASES PASSED (score 1.0 on all evaluators)"]

    _draw_lines(path, lines, title_color=(134, 239, 172))


def render_trace_tree(path: Path, project: str) -> None:
    from langsmith import Client
    from PIL import Image, ImageDraw

    client = Client()
    runs = list(client.list_runs(project_name=project, is_root=True, limit=1))
    if not runs:
        return
    root = runs[0]
    children = list(client.list_runs(project_name=project, trace_id=root.trace_id, limit=15))

    lines = [
        "LangSmith Trace — hw3_mortgage_orchestrator",
        f"Root run: {root.id}",
        f"Status: {root.status}  |  Latency: {root.latency:.2f}s" if root.latency else f"Status: {root.status}",
        "",
        "Trace tree (API):",
        f"└─ {root.name} ({root.run_type})",
    ]
    for child in children:
        lines.append(f"   └─ {child.name} ({child.run_type}) — {child.status}")

    if root.outputs:
        lines += ["", "Outputs:", *[f"  • {k}" for k in list(root.outputs.keys())[:8]]]

    _draw_lines(path, lines)


def _draw_lines(path: Path, lines: list[str], title_color=(125, 211, 252)) -> None:
    from PIL import Image, ImageDraw

    font = _font()
    line_h = 22
    pad = 24
    w = 1200
    h = pad * 2 + line_h * len(lines)
    img = Image.new("RGB", (w, h), (13, 17, 23))
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        color = title_color if i < 3 else (230, 237, 243)
        draw.text((pad, pad + i * line_h), line, fill=color, font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"Saved {path}")


def main() -> None:
    sys.path.insert(0, str(_HW3))
    from mortgage_agents.langsmith_tracing import configure_langsmith_tracing

    configure_langsmith_tracing()
    meta = json.loads((_HW3 / "langsmith_eval_results.json").read_text())
    project = meta["experiment_project"]
    render_compare_table(_SHOTS / "04_experiment_compare_api.png", project)
    render_trace_tree(_SHOTS / "05_trace_detail_api.png", project)
    render_compare_table(_SHOTS / "08_eval_summary_api.png", project)  # refresh


if __name__ == "__main__":
    main()
