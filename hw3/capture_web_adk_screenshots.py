#!/usr/bin/env python3
"""Capture ADK Web UI screenshots for each README sample prompt."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

_HW3 = Path(__file__).resolve().parent
_JSON = _HW3 / "sample_prompt_outputs.json"
_WEB_SHOTS = _HW3 / "web_screenshots"
_MD = _HW3 / "HW3_Web_ADK_Sample_Outputs.md"
_BASE_URL = "http://127.0.0.1:8000/dev-ui/"

AGENT_MAP = {
    "mortgage_supervisor_full": "mortgage_supervisor",
    "mortgage_supervisor_compare": "mortgage_supervisor",
    "rate_finder": "rate_finder",
    "payment_calculator": "payment_calculator",
    "affordability_analyzer": "affordability_analyzer",
    "compliance_critic": "compliance_critic",
}

# mortgage_supervisor needs longer runs
TIMEOUT_MS = {
    "mortgage_supervisor": 180_000,
    "default": 90_000,
}


def _slug(title: str, index: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"{index:02d}_{base[:50]}"


def select_app(page, agent_name: str) -> None:
    page.goto(_BASE_URL, wait_until="networkidle")
    page.get_by_role("button", name="Select an app").click()
    page.get_by_placeholder("Search apps...").fill(agent_name)
    page.get_by_role("button", name=agent_name, exact=True).click(force=True)
    page.wait_for_timeout(1500)


def send_prompt(page, prompt: str) -> None:
    textarea = page.locator("textarea").first
    textarea.wait_for(state="visible", timeout=15_000)
    textarea.fill(prompt)
    page.keyboard.press("Enter")
    send_btn = page.locator("button[aria-label*='Send'], button:has(mat-icon:has-text('send'))")
    if send_btn.count() > 0:
        try:
            send_btn.first.click(timeout=2000)
        except Exception:
            pass


def wait_for_response(page, agent_name: str) -> None:
    timeout = TIMEOUT_MS.get(agent_name, TIMEOUT_MS["default"])
    deadline = time.time() + timeout / 1000

    while time.time() < deadline:
        body = page.inner_text("body")
        # Final responses usually include disclaimer or formatted markdown
        if len(body) > 2200 and (
            "Educational" in body
            or "educational" in body
            or "APPROVED" in body
            or "REVISE" in body
            or "**" in body
        ):
            page.wait_for_timeout(2500)
            return
        page.wait_for_timeout(2000)

    print(f"  Warning: timed out waiting for final response ({agent_name})", flush=True)


def screenshot_chat_and_trace(page, chat_path: Path, trace_path: Path) -> None:
    chat_path.parent.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(800)
    page.screenshot(path=str(chat_path), full_page=True)

    # Agent graph / trace panel (account_tree toggles structural view)
    tree_btn = page.get_by_role("button", name="account_tree")
    if tree_btn.count():
        tree_btn.click()
        page.wait_for_timeout(1200)
        page.screenshot(path=str(trace_path), full_page=True)
    else:
        trace_path.write_bytes(chat_path.read_bytes())


def build_markdown(items: list[dict], shots: list[tuple[Path, Path]]) -> str:
    lines = [
        "# HW3 Web ADK Sample Outputs",
        "",
        "Screenshots from the **ADK Dev UI** (`adk web`) for each README sample prompt.",
        "",
        f"Captured from `{_BASE_URL}` using Doubleword/LiteLLM.",
        "",
        "> Educational outputs only. Not financial advice.",
        "",
        "---",
        "",
    ]

    for i, (item, (chat, trace)) in enumerate(zip(items, shots), start=1):
        agent = AGENT_MAP.get(item["agent"], item["agent"])
        lines += [
            f"## {i}. {item['title']}",
            "",
            f"**Web agent:** `{agent}`",
            "",
            "### Chat",
            "",
            f"![{item['title']} chat]({chat.relative_to(_HW3).as_posix()})",
            "",
            "### Trace",
            "",
            f"![{item['title']} trace]({trace.relative_to(_HW3).as_posix()})",
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

    lines += [
        "## Regenerate",
        "",
        "```bash",
        "# Terminal 1 — start web UI",
        "cd src && uv run adk web ../hw3/adk_agents --port 8000",
        "",
        "# Terminal 2 — capture screenshots + markdown",
        "cd src && uv run --with playwright python ../hw3/capture_web_adk_screenshots.py",
        "uv run playwright install chromium",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    if not _JSON.is_file():
        raise SystemExit(f"Missing {_JSON}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Install playwright: cd src && uv run --with playwright python ../hw3/capture_web_adk_screenshots.py"
        ) from exc

    items = json.loads(_JSON.read_text(encoding="utf-8"))
    shot_pairs: list[tuple[Path, Path]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        for i, item in enumerate(items, start=1):
            slug = _slug(item["title"], i)
            agent = AGENT_MAP[item["agent"]]
            chat_path = _WEB_SHOTS / f"{slug}_chat.png"
            trace_path = _WEB_SHOTS / f"{slug}_trace.png"

            print(f"=== {item['title']} ({agent}) ===", flush=True)
            select_app(page, agent)
            send_prompt(page, item["prompt"])
            wait_for_response(page, agent)
            screenshot_chat_and_trace(page, chat_path, trace_path)
            shot_pairs.append((chat_path, trace_path))
            print(f"  Saved {chat_path.name}, {trace_path.name}", flush=True)

        browser.close()

    _MD.write_text(build_markdown(items, shot_pairs), encoding="utf-8")
    print(f"\nWrote {_MD}")


if __name__ == "__main__":
    main()
