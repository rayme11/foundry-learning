"""
Chapter 2: File Search with a Vector Store (chat script)
========================================================
Ask questions about nu_staff_handbook.pdf. The model automatically
searches the document via the built-in `file_search` tool and cites
its sources.

PREREQUISITE — run the one-time setup first:

    python Chapter2-Tools/setup_vector_store.py

That uploads the PDF, creates the vector store, and saves
AZURE_VECTOR_STORE_ID to the root .env. This script reuses that store,
so there's no re-uploading or re-indexing on every run.
"""
import os
import sys
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

# Vector store created by setup_vector_store.py
vector_store_id = os.getenv("AZURE_VECTOR_STORE_ID")
if not vector_store_id:
    print("❌ AZURE_VECTOR_STORE_ID not set. Run setup first:")
    print("   python Chapter2-Tools/setup_vector_store.py")
    sys.exit(1)

# --- ANSI colors (same style as Chapter 1) ---
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------
# Ask questions — the model searches the doc automatically.
# Attaching the file_search tool lets the model decide WHEN to search.
# ---------------------------------------------------------------
def chat_with_handbook(vs_id: str):
    tools = [{"type": "file_search", "vector_store_ids": [vs_id]}]
    last_response_id = None

    print(f"{BOLD}{GREEN}Assistant:{RESET} Ask me anything about the staff handbook!")
    print(f"{DIM}Type 'quit' or 'exit' to stop.{RESET}")

    while True:
        try:
            input_text = input(f"\n{BOLD}{BLUE}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{BOLD}{GREEN}Assistant:{RESET} Goodbye! 👋{RESET}")
            break

        if not input_text:
            continue
        if input_text.lower() in ("quit", "exit"):
            print(f"{BOLD}{GREEN}Assistant:{RESET} Goodbye! 👋{RESET}")
            break

        response = client.responses.create(
            model=deployment_name,
            instructions=(
                "You are an HR assistant. Answer questions using the staff "
                "handbook via the file_search tool. If the handbook doesn't "
                "cover it, say so."
            ),
            input=input_text,
            tools=tools,
            include=["file_search_call.results"],  # return search snippets
            previous_response_id=last_response_id,
        )

        print(f"\n{BOLD}{GREEN}Assistant:{RESET} {response.output_text}")
        print(f"{DIM}[in: {response.usage.input_tokens} | out: {response.usage.output_tokens} "
              f"| id: {response.id}]{RESET}")

        # Show which parts of the handbook were used
        for item in response.output:
            if item.type == "file_search_call":
                queries = getattr(item, "queries", None) or []
                print(f"{DIM}   🔎 searched: {queries}{RESET}")

        last_response_id = response.id


if __name__ == "__main__":
    chat_with_handbook(vector_store_id)
