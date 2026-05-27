"""
Tool functions for the HW1 agent.

Each tool is a regular Python function with type hints and a docstring.
The google-genai SDK will inspect these to generate the tool schema that
the model sees when deciding which tool to call.
"""

# Case-insensitive lookup table for a few cities.
_WEATHER_BY_CITY: dict[str, str] = {
    "tokyo": "Partly cloudy, 18°C (64°F)",
    "london": "Rainy, 12°C (54°F)",
    "new york": "Sunny, 22°C (72°F)",
    "san francisco": "Foggy, 16°C (61°F)",
    "paris": "Overcast, 14°C (57°F)",
    "sydney": "Clear, 24°C (75°F)",
}


def get_weather(city: str) -> str:
    """Get the current weather report for a given city.

    Args:
        city (str): The name of the city to look up weather for.

    Returns:
        str: A short, human-readable description of the weather.
    """
    key = city.strip().lower()
    if key in _WEATHER_BY_CITY:
        return f"{city.strip()}: {_WEATHER_BY_CITY[key]}"

    return (
        f"Weather data not available for {city}. "
        f"Known cities: {', '.join(c.title() for c in _WEATHER_BY_CITY)}."
    )


def add_numbers(a: float, b: float) -> float:
    """Add two numbers together and return the sum.

    Args:
        a (float): The first number.
        b (float): The second number.

    Returns:
        float: The sum of a and b.
    """
    return a + b


# Registry of tools the agent is allowed to call.
AVAILABLE_TOOLS = [
    get_weather,
    add_numbers,
]
