"""
HW1 — Simple AI agent built on the google-genai SDK (NOT google-adk).

What you'll build:
    A small ReAct-style agent that runs in a loop:
        1. Send the user prompt (plus any prior turns) to Gemini.
        2. If the model wants to call a tool, execute it locally and
           feed the result back to the model.
        3. Repeat until the model returns a plain text answer.

The agent exposes two tools (defined in tools.py):
    * get_weather(city)       — look up the weather for a city
    * add_numbers(a, b)       — add two numbers

Run it interactively:
    python -m hw1-skeleton.agent
        or
    cd src/hw1-skeleton && python agent.py

Make sure GOOGLE_API_KEY is set in your environment (see ../.env).
"""

import os
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import AVAILABLE_TOOLS


# Cap the agent loop so a misbehaving model can't spin forever.
MAX_AGENT_STEPS = 6


def get_client() -> genai.Client:
    """Build a google-genai client from the GOOGLE_API_KEY env var."""
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
    """Run a single tool the model asked for and return its result.

    Args:
        function_call: The FunctionCall object emitted by the model.
        tools_by_name: Mapping of tool name -> Python callable.

    Returns:
        Whatever the tool function returns (will be serialized back to
        the model as the function response).
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
    except Exception as e:
        # Return the error to the model so it can recover instead of crashing.
        return {"error": f"{type(e).__name__}: {e}"}


def run_agent(client: genai.Client, model: str, user_prompt: str) -> str:
    """Run the agent loop for a single user prompt.

    TODO (students): fill in the loop.

    Suggested shape:
        1. Build a `contents` list seeded with the user's message:
               contents = [types.Content(role="user",
                                          parts=[types.Part(text=user_prompt)])]
        2. Build a GenerateContentConfig with:
               tools=AVAILABLE_TOOLS,
               and set function_calling mode to "AUTO" via
               types.ToolConfig(function_calling_config=...)
           IMPORTANT: pass `automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)`
           so the SDK does NOT auto-execute tools — we want to drive the loop ourselves.
        3. Loop up to MAX_AGENT_STEPS times:
             a. Call client.models.generate_content(model=..., contents=contents, config=...)
             b. Look at response.candidates[0].content.parts.
             c. If any part has a `function_call`, execute it with
                execute_tool_call() and append BOTH the model's content
                AND a new types.Content(role="user", parts=[Part(function_response=...)])
                back into `contents`. Then continue the loop.
             d. Otherwise, return the text from response.text.
        4. If the loop hits MAX_AGENT_STEPS without a final answer, return a
           helpful error string.
    """
    tools_by_name = {fn.__name__: fn for fn in AVAILABLE_TOOLS}

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part(text=user_prompt)],
        )
    ]

    config = types.GenerateContentConfig(
        tools=AVAILABLE_TOOLS,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )

    for step in range(MAX_AGENT_STEPS):
        print(f"\n--- agent step {step + 1} ---")

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        if not response.candidates or not response.candidates[0].content:
            return "No response from model."

        model_content = response.candidates[0].content
        parts = model_content.parts or []

        function_calls = [
            part.function_call for part in parts if part.function_call is not None
        ]

        if function_calls:
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
            continue

        if response.text:
            return response.text.strip()

        text_parts = [part.text for part in parts if part.text]
        if text_parts:
            return "\n".join(text_parts).strip()

    return "Agent stopped: hit MAX_AGENT_STEPS without producing a final answer."


def repl(client: genai.Client, model: str) -> None:
    """Tiny interactive loop so you can chat with the agent from the terminal."""
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
        except NotImplementedError as e:
            print(f"[not implemented] {e}")
            continue
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")
            continue

        print(f"agent > {answer}\n")


def main() -> None:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    client = get_client()
    repl(client, model)


if __name__ == "__main__":
    main()
