"""
Chapter 2 — ONE-TIME SETUP: Upload PDF & create vector store
============================================================
Run this ONCE (or whenever the PDF changes):

    python Chapter2-Tools/setup_vector_store.py

It uploads nu_staff_handbook.pdf, creates a vector store, waits for
indexing, then writes AZURE_VECTOR_STORE_ID to the root .env so the
chat script (FileSearchVectorStore.py) can reuse it — no re-uploading,
no re-indexing on every run.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from dotenv import load_dotenv, find_dotenv, set_key
from openai import OpenAI

load_dotenv(find_dotenv())

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]

# Auth: API key if available, otherwise Entra ID
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if api_key:
    auth = api_key
else:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    auth = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")

# Generous timeout for the multi-MB upload (default can stall on large files)
client = OpenAI(base_url=endpoint, api_key=auth, timeout=300.0)

# Prefer a local staging copy — reading large files from cloud-synced
# folders (Google Drive) stalls the upload. Falls back to the repo copy.
_LOCAL_COPY = Path.home() / "tmp" / "foundry-upload" / "nu_staff_handbook.pdf"
_REPO_COPY = Path(__file__).parent / "nu_staff_handbook.pdf"
PDF_PATH = _LOCAL_COPY if _LOCAL_COPY.exists() else _REPO_COPY

DIM = "\033[90m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def main():
    if not PDF_PATH.exists():
        print(f"{YELLOW}❌ File not found: {PDF_PATH}{RESET}")
        sys.exit(1)

    # 1. Upload the PDF
    # Copy to a local temp file first — reading large files directly from
    # cloud-synced folders (Google Drive/iCloud) can stall the upload.
    print(f"{DIM}📤 Uploading {PDF_PATH.name} ({PDF_PATH.stat().st_size / 1e6:.1f} MB) ...{RESET}")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfile(PDF_PATH, tmp.name)
        with open(tmp.name, "rb") as f:
            file_obj = client.files.create(
                file=(PDF_PATH.name, f, "application/pdf"),
                purpose="assistants",
            )
    os.unlink(tmp.name)
    print(f"{DIM}   → file id: {file_obj.id}{RESET}")

    # 2. Create vector store + attach file (indexing is async)
    print(f"{DIM}🗄️  Creating vector store ...{RESET}")
    vs = client.vector_stores.create(name="nu-staff-handbook-store")

    print(f"{DIM}📎 Attaching file — indexing chunks + embeddings ...{RESET}")
    client.vector_stores.files.create(vector_store_id=vs.id, file_id=file_obj.id)

    start = time.time()
    while True:
        status = client.vector_stores.files.retrieve(
            vector_store_id=vs.id, file_id=file_obj.id
        )
        elapsed = int(time.time() - start)
        print(f"{DIM}   … {status.status} ({elapsed}s elapsed){RESET}", end="\r")
        if status.status == "completed":
            print()  # newline after the progress line
            break
        if status.status == "failed":
            print(f"\n{YELLOW}❌ Indexing failed: {status.last_error}{RESET}")
            sys.exit(1)
        time.sleep(2)

    # 3. Persist the store ID in the root .env for reuse
    env_path = find_dotenv()
    set_key(env_path, "AZURE_VECTOR_STORE_ID", vs.id)

    print(f"{GREEN}✅ Setup complete!{RESET}")
    print(f"   Vector store: {vs.id}")
    print(f"   Saved AZURE_VECTOR_STORE_ID to {env_path}")
    print(f"\nNow run: python Chapter2-Tools/FileSearchVectorStore.py")


if __name__ == "__main__":
    main()
