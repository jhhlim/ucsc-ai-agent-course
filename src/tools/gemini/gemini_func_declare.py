import os
from google import genai
from google.genai import types

from dotenv import load_dotenv


def get_client() -> genai.Client:
    """Get a configured Google GenAI client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    return genai.Client(api_key=api_key)


# 1. Define the Python function the model can call
def get_stock_price(ticker: str, currency: str = "USD") -> str:
    """Retrieves the current stock price for a given ticker symbol.

    Args:
        ticker: The stock symbol (e.g., 'GOOG', 'AAPL').
        currency: The currency to return the price in. Defaults to 'USD'.
    """
    # In a real app, you would fetch live data here
    if ticker.upper() == "GOOG":
        return f"180 {currency}"
    return f"Data not found for {ticker}"

def main():
    client = get_client()
    # 2. Automatically generate the declaration from your Python function
    func_declaration = types.FunctionDeclaration.from_callable(
        client=client,
        callable=get_stock_price
    )

    # 3. Wrap it in a Tool object
    tools = [types.Tool(function_declarations=[func_declaration])]

    # 4. Pass the tool to the model
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="Can you check the stock price for GOOG in EUR?",
        config=types.GenerateContentConfig(
            tools=tools
        )
    )

    # 5. Check if the model decided to call your function
    if response.function_calls:
        for call in response.function_calls:
            print(f"Model wants to call function: '{call.name}'")
            print(f"Arguments provided by model: {call.args}")
    else:
        print("Response text:", response.text)

# ANSI color codes — terminal output only. Strip if you pipe to a file.
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"

if __name__ == "__main__":
    bar = "=" * 70
    print(f"\n{CYAN}{bar}{RESET}")
    print(f"{BOLD}{CYAN} Running Gemini function declaration example...{RESET}")
    print(f"{CYAN}{bar}{RESET}")
    load_dotenv()
    main()