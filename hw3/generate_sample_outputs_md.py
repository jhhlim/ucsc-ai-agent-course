#!/usr/bin/env python3
"""Build HW3 sample outputs as terminal screenshots in a Markdown file."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

_HW3 = Path(__file__).resolve().parent
_JSON = _HW3 / "sample_prompt_outputs.json"
_SCREENSHOTS = _HW3 / "screenshots"
_MD = _HW3 / "HW3_Sample_Prompt_Outputs.md"

ADK_AGENT_DIR = {
    "mortgage_supervisor_full": "mortgage_supervisor",
    "mortgage_supervisor_compare": "mortgage_supervisor",
    "rate_finder": "rate_finder",
    "payment_calculator": "payment_calculator",
    "affordability_analyzer": "affordability_analyzer",
    "compliance_critic": "compliance_critic",
}

# Terminal colors
BG = (13, 17, 23)
PROMPT_COLOR = (125, 211, 252)  # cyan
CMD_COLOR = (163, 113, 247)  # purple
USER_COLOR = (134, 239, 172)  # green
AGENT_COLOR = (250, 204, 21)  # yellow
TEXT_COLOR = (230, 237, 243)
MUTED = (139, 148, 158)


def _slug(title: str, index: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"{index:02d}_{base[:50]}"


def _wrap_lines(text: str, width: int = 96) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if not raw.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(raw, width=width, replace_whitespace=False) or [""])
    return lines


def _terminal_lines(item: dict) -> list[tuple[str, tuple[int, int, int]]]:
    adk_agent = ADK_AGENT_DIR.get(item["agent"], item["agent"])
    lines: list[tuple[str, tuple[int, int, int]]] = []

    def add(text: str, color: tuple[int, int, int] = TEXT_COLOR) -> None:
        lines.append((text, color))

    add("$ cd src", CMD_COLOR)
    add(f"$ uv run adk run ../hw3/adk_agents/{adk_agent}", CMD_COLOR)
    add("Running agent mortgage_supervisor, type exit to exit." if "supervisor" in adk_agent else f"Running agent {adk_agent}, type exit to exit.", MUTED)
    add("[user]:", USER_COLOR)
    for pline in item["prompt"].splitlines():
        add(f"  {pline}", USER_COLOR)
    add("", TEXT_COLOR)
    author = adk_agent if adk_agent != "mortgage_supervisor" else "mortgage_supervisor"
    add(f"[{author}]:", AGENT_COLOR)
    for oline in _wrap_lines(item["response"]):
        add(f"  {oline}" if oline else "", TEXT_COLOR)
    return lines


def render_terminal_png(lines: list[tuple[str, tuple[int, int, int]]], path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    font_size = 15
    line_height = 20
    pad_x, pad_y = 24, 24
    width = 1280

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    height = pad_y * 2 + line_height * len(lines)
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    y = pad_y
    for text, color in lines:
        draw.text((pad_x, y), text, fill=color, font=font)
        y += line_height

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def build_markdown(items: list[dict], image_paths: list[Path]) -> str:
    parts = [
        "# HW3 Sample Prompt Outputs (Terminal Screenshots)",
        "",
        "Berryessa **$1.28M** scenario — captured from `adk run` sessions via Doubleword/LiteLLM.",
        "",
        "> Educational outputs only. Not financial advice.",
        "",
        "---",
        "",
    ]

    for i, (item, img_path) in enumerate(zip(items, image_paths), start=1):
        rel = img_path.relative_to(_HW3).as_posix()
        parts.extend(
            [
                f"## {i}. {item['title']}",
                "",
                f"**Agent:** `{ADK_AGENT_DIR.get(item['agent'], item['agent'])}`",
                "",
                f"![{item['title']}]({rel})",
                "",
                "<details>",
                "<summary>Prompt text</summary>",
                "",
                "```text",
                item["prompt"].strip(),
                "```",
                "",
                "</details>",
                "",
                "---",
                "",
            ]
        )

    parts.extend(
        [
            "## Regenerate",
            "",
            "```bash",
            "# 1. Refresh JSON from live agents",
            "cd src && uv run python ../hw3/collect_sample_outputs.py --json-only",
            "",
            "# 2. Rebuild screenshots + this markdown",
            "cd src && uv run --with pillow python ../hw3/generate_sample_outputs_md.py",
            "```",
            "",
        ]
    )
    return "\n".join(parts)


def main() -> None:
    if not _JSON.is_file():
        raise SystemExit(f"Missing {_JSON}. Run collect_sample_outputs.py first.")

    items = json.loads(_JSON.read_text(encoding="utf-8"))
    image_paths: list[Path] = []

    for i, item in enumerate(items, start=1):
        slug = _slug(item["title"], i)
        img_path = _SCREENSHOTS / f"{slug}.png"
        lines = _terminal_lines(item)
        render_terminal_png(lines, img_path)
        image_paths.append(img_path)
        print(f"Wrote {img_path}")

    _MD.write_text(build_markdown(items, image_paths), encoding="utf-8")
    print(f"Wrote {_MD}")


if __name__ == "__main__":
    main()
