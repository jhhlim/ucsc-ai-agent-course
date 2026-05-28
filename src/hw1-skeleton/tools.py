"""
Tool functions for the HW1 agent.

Each tool is a regular Python function with type hints and a docstring.
The google-genai SDK inspects these to build the tool schema the model uses
when deciding whether to call a function.

Tools:
    get_weather(city)   — live weather via wttr.in (https://github.com/chubin/wttr.in)
    add_numbers(a, b)   — arithmetic helper
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

# wttr.in blocks generic clients; send a descriptive User-Agent.
_WTTR_USER_AGENT = "ucsc-hw1-agent/1.0 (course homework; +https://github.com/chubin/wttr.in)"
_WTTR_TIMEOUT_SEC = 15


def _fetch_wttr_json(city: str) -> dict:
    """Request current weather JSON from wttr.in for a city name."""
    location = urllib.parse.quote(city.strip())
    url = f"https://wttr.in/{location}?format=j1"
    request = urllib.request.Request(url, headers={"User-Agent": _WTTR_USER_AGENT})
    with urllib.request.urlopen(request, timeout=_WTTR_TIMEOUT_SEC) as response:
        return json.loads(response.read().decode())


def _format_weather_report(city: str, data: dict) -> str:
    """Turn wttr.in JSON into a concise, human-readable weather summary."""
    current = data["current_condition"][0]

    # Prefer the resolved place name from the API when available.
    area_name = city.strip()
    nearest = data.get("nearest_area") or []
    if nearest:
        names = nearest[0].get("areaName") or []
        if names:
            area_name = names[0].get("value", area_name)

    description = current["weatherDesc"][0]["value"]
    temp_c = current["temp_C"]
    temp_f = current["temp_F"]
    feels_c = current.get("FeelsLikeC", temp_c)
    humidity = current.get("humidity", "?")
    wind_kmph = current.get("windspeedKmph", "?")
    wind_dir = current.get("winddir16Point", "")

    wind_part = f"{wind_kmph} km/h"
    if wind_dir:
        wind_part += f" {wind_dir}"

    return (
        f"{area_name}: {description}, {temp_c}°C ({temp_f}°F), "
        f"feels like {feels_c}°C, humidity {humidity}%, wind {wind_part}."
    )


def get_weather(city: str) -> str:
    """Get the current weather report for a given city.

    Fetches live data from wttr.in (no API key required). The model should
    pass a city name such as "Tokyo", "London", or "New York".

    Args:
        city: Name of the city or location to look up.

    Returns:
        A short, human-readable weather summary, or an error message if the
        lookup fails (unknown location, network error, timeout).
    """
    city = city.strip()
    if not city:
        return "Error: city name cannot be empty."

    try:
        data = _fetch_wttr_json(city)
        return _format_weather_report(city, data)
    except urllib.error.HTTPError as exc:
        return f"Error: weather service returned HTTP {exc.code} for {city!r}."
    except urllib.error.URLError as exc:
        return f"Error: could not reach weather service ({exc.reason})."
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return f"Error: unexpected weather data format ({exc})."
    except TimeoutError:
        return f"Error: weather lookup timed out for {city!r}."


def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return the sum.

    The model uses this tool when the user asks for arithmetic (e.g. "17 plus 25").
    Arguments are coerced to floats by the SDK from the model's JSON args.

    Args:
        a: First addend.
        b: Second addend.

    Returns:
        The sum a + b as a float.
    """
    return float(a) + float(b)


# Tools registered with Gemini via GenerateContentConfig(tools=AVAILABLE_TOOLS).
AVAILABLE_TOOLS = [
    get_weather,
    add_numbers,
]
