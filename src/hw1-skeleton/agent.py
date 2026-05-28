"""
HW1 — Simple AI agent built on the google-genai SDK (NOT google-adk).

Agent loop (manual function calling):
    1. Send the user prompt (and prior turns) to Gemini with tool declarations.
    2. Read response.candidates[0].content.parts — check part.function_call vs part.text.
    3. If the model requested tools, run them locally and append function_response
       parts back into contents, then call the model again.
    4. Repeat until the model returns plain text or MAX_AGENT_STEPS is reached.

Tools are defined in tools.py (get_weather via wttr.in, add_numbers).

Run:
    cd src/hw1-skeleton && ../.venv/bin/python agent.py

Requires GOOGLE_API_KEY in src/.env (see ../env.example).

Reference: https://ai.google.dev/gemini-api/docs/function-calling
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from tools import AVAILABLE_TOOLS

# Prevent infinite tool-calling loops if the model never returns text.
MAX_AGENT_STEPS = 6

# Retry transient Gemini overload / rate-limit errors (e.g. 503 UNAVAILABLE).
MAX_API_RETRIES = 4
RETRY_BASE_DELAY_SEC = 2
_RETRYABLE_STATUS_CODES = {429, 500, 503}


def get_client() -> genai.Client:
    """Create a Gemini client using GOOGLE_API_KEY from the environment."""
    api_key = (os.getenv("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key or api_key == "<your key>" or not api_key.startswith("AIza"):
        raise ValueError(
            "GOOGLE_API_KEY is not set. Add it to src/.env (see env.example)."
        )
    return genai.Client(api_key=api_key)


def execute_tool_call(
    function_call: types.FunctionCall,
    tools_by_name: dict[str, Callable[..., Any]],
) -> Any:
    """Execute one tool the model requested and return a JSON-serializable result.

    Args:
        function_call: Part.function_call from the model response.
        tools_by_name: Map of tool name -> Python callable.

    Returns:
        Tool return value, or {"error": "..."} so the model can recover.
    """
    name = function_call.name
    args = dict(function_call.args or {})

    if name not in tools_by_name:
        return {"error": f"Unknown tool: {name}"}

    print(f"  >> tool call: {name}({args})")
    try:
        result = tools_by_name[name](**args)
        print(f"  >> tool result: {result}")
        return result
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _is_retryable_api_error(exc: BaseException) -> bool:
    """True for temporary server overload (503) or rate limits (429)."""
    if isinstance(exc, genai_errors.ServerError):
        return getattr(exc, "code", None) in _RETRYABLE_STATUS_CODES
    return False


def _generate_content_with_retry(
    client: genai.Client,
    model: str,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
) -> types.GenerateContentResponse:
    """Call Gemini with exponential backoff on 429/503/500."""
    last_error: BaseException | None = None
    for attempt in range(MAX_API_RETRIES):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_error = exc
            if not _is_retryable_api_error(exc) or attempt >= MAX_API_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY_SEC * (2**attempt)
            print(
                f"  >> model busy ({getattr(exc, 'code', 'unknown')}), "
                f"retrying in {delay}s..."
            )
            time.sleep(delay)
    raise last_error  # pragma: no cover


def _build_generate_config() -> types.GenerateContentConfig:
    """Register tools and disable SDK auto-execution so we control the loop."""
    return types.GenerateContentConfig(
        tools=AVAILABLE_TOOLS,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        ),
        # We append function_response ourselves; do not let the SDK run tools.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )


def _extract_function_calls(parts: list[types.Part]) -> list[types.FunctionCall]:
    """Collect all function_call objects from the model's content parts."""
    return [
        part.function_call
        for part in parts
        if part.function_call is not None
    ]


def _extract_text_answer(
    response: types.GenerateContentResponse,
    parts: list[types.Part],
) -> str | None:
    """Return final text from response.text or from text parts, if present."""
    if response.text:
        return response.text.strip()

    text_parts = [part.text for part in parts if part.text]
    if text_parts:
        return "\n".join(text_parts).strip()

    return None


def _append_tool_results(
    contents: list[types.Content],
    model_content: types.Content,
    function_calls: list[types.FunctionCall],
    tools_by_name: dict[str, Callable[..., Any]],
) -> None:
    """Append model tool requests and user-role function_response parts to contents.

    Per Gemini function-calling docs, send tool results as a Content with
    role "user" containing Part(function_response=FunctionResponse(...)).
    """
    contents.append(model_content)

    response_parts: list[types.Part] = []
    for function_call in function_calls:
        result = execute_tool_call(function_call, tools_by_name)
        response_parts.append(
            types.Part(
                function_response=types.FunctionResponse(
                    id=function_call.id,
                    name=function_call.name,
                    response={"result": result},
                )
            )
        )

    contents.append(types.Content(role="user", parts=response_parts))


def run_agent(client: genai.Client, model: str, user_prompt: str) -> str:
    """Run the ReAct-style tool loop for one user message.

    Args:
        client: Configured google-genai client.
        model: Gemini model id (e.g. gemini-2.5-flash).
        user_prompt: The user's natural-language request.

    Returns:
        Final assistant text, or an error / step-limit message.
    """
    tools_by_name = {fn.__name__: fn for fn in AVAILABLE_TOOLS}
    config = _build_generate_config()

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part(text=user_prompt)],
        )
    ]

    for step in range(MAX_AGENT_STEPS):
        print(f"\n--- agent step {step + 1} ---")

        response = _generate_content_with_retry(client, model, contents, config)

        if not response.candidates or not response.candidates[0].content:
            return "No response from model."

        # Hint: model output lives at response.candidates[0].content
        model_content = response.candidates[0].content
        parts = model_content.parts or []

        function_calls = _extract_function_calls(parts)
        if function_calls:
            _append_tool_results(contents, model_content, function_calls, tools_by_name)
            continue

        final_text = _extract_text_answer(response, parts)
        if final_text:
            return final_text

    return (
        f"Agent stopped: hit MAX_AGENT_STEPS ({MAX_AGENT_STEPS}) "
        "without producing a final answer."
    )


def repl(client: genai.Client, model: str) -> None:
    """Interactive read-eval-print loop for trying prompts in the terminal."""
    print(f"HW1 agent ready (model={model}). Type 'exit' or Ctrl-D to quit.\n")
    while True:
        try:
            user_input = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        try:
            answer = run_agent(client, model, user_input)
        except NotImplementedError as exc:
            print(f"[not implemented] {exc}")
            continue
        except Exception as exc:
            print(f"[error] {type(exc).__name__}: {exc}")
            continue

        print(f"agent > {answer}\n")


def main() -> None:
    """Load env, build client, and start the REPL."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    client = get_client()
    repl(client, model)


if __name__ == "__main__":
    main()
