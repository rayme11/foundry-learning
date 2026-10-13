import os
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

load_dotenv(find_dotenv())

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

# Auth: use API key if available, otherwise fall back to Entra ID (requires `az login`)
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if api_key:
    auth = api_key
else:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    auth = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")

client = OpenAI(
    base_url=endpoint,
    api_key=auth
)

# --- ANSI colors for a friendly terminal UI ---
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
DIM = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

# --- Cost tracking (gpt-4.1 pricing: $2.00 / 1M input tokens, $8.00 / 1M output tokens) ---
PRICE_PER_1M_INPUT = 2.00
PRICE_PER_1M_OUTPUT = 8.00

# Conversation history: list of turns with stats
history = []
last_response_id = None
turn = 0


def print_dashboard():
    """Show cumulative session stats — watch input tokens grow each turn!"""
    total_in = sum(t["input_tokens"] for t in history)
    total_out = sum(t["output_tokens"] for t in history)
    cost = (total_in / 1_000_000 * PRICE_PER_1M_INPUT) + (total_out / 1_000_000 * PRICE_PER_1M_OUTPUT)
    print(f"\n{CYAN}{'─' * 60}")
    print(f" 📊 SESSION: {turn} turns | in: {total_in} | out: {total_out} "
          f"| total: {total_in + total_out} | est. cost: ${cost:.6f}")
    print(f"{'─' * 60}{RESET}")


print(f"{BOLD}{GREEN}Assistant:{RESET} Chat ready! Model: {YELLOW}{deployment_name}{RESET}")
print(f"{DIM}Commands: 'quit' to exit | 'reset' to clear context | 'history' to review turns{RESET}")
print(f"{DIM}💡 Watch how INPUT tokens grow each turn — the whole conversation is resent!{RESET}")

while True:
    try:
        input_text = input(f"\n{BOLD}{BLUE}You:{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{BOLD}{GREEN}Assistant:{RESET} Goodbye! 👋")
        break

    if not input_text:
        continue

    if input_text.lower() in ("quit", "exit"):
        print(f"{BOLD}{GREEN}Assistant:{RESET} Goodbye! 👋")
        break

    if input_text.lower() == "reset":
        history.clear()
        last_response_id = None
        turn = 0
        print(f"{YELLOW}🔄 Conversation reset — starting fresh.{RESET}")
        continue

    if input_text.lower() == "history":
        print(f"\n{MAGENTA}{BOLD}📜 Conversation History:{RESET}")
        for t in history:
            print(f"\n{DIM}── Turn {t['turn']} ──{RESET}")
            print(f"{BLUE}You:{RESET} {t['user']}")
            print(f"{GREEN}Assistant:{RESET} {t['assistant'][:120]}{'...' if len(t['assistant']) > 120 else ''}")
            print(f"{DIM}   in: {t['input_tokens']} | out: {t['output_tokens']} "
                  f"| id: {t['response_id']}{RESET}")
        continue

    # Get a response, chained to the previous turn for context
    response = client.responses.create(
        model=deployment_name,
        instructions="You are a helpful AI assistant that explains technology concepts clearly.",
        input=input_text,
        previous_response_id=last_response_id,
    )

    turn += 1
    usage = response.usage

    # Record this turn
    history.append({
        "turn": turn,
        "user": input_text,
        "assistant": response.output_text,
        "response_id": response.id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    })

    print(f"\n{BOLD}{GREEN}Assistant:{RESET} {response.output_text}")
    current = history[-1]
    print(f"{DIM}[turn {current['turn']} | in: {current['input_tokens']} | out: {current['output_tokens']} "
          f"| id: {current['response_id']}]{RESET}")

    last_response_id = response.id
    print_dashboard()

print_dashboard()