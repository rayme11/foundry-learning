"""
Chapter 3: Batch evaluation with the Azure AI Evaluation SDK
============================================================
Runs built-in, AI-assisted quality evaluators over eval_data.jsonl and
prints aggregate metrics. The model deployment named in
AZURE_OPENAI_DEPLOYMENT_NAME acts as the *judge* that scores each row.

Evaluators used:
  - Groundedness  — is the response supported by the context? (1-5)
  - Relevance     — does the response address the query?        (1-5)
  - Coherence     — does the response read logically?           (1-5)
  - Fluency       — is the response grammatically well-written? (1-5)
  - Similarity    — semantic closeness to ground truth          (1-5)
  - F1 score      — token overlap vs. ground truth              (0-1)

Note: row 5 of eval_data.jsonl intentionally contains a WRONG answer
("Kyoto" instead of "Tokyo") so you can see low scores in action.

Run:
    python Chapter3-Evaluations/run_evaluation.py

Results are written to Chapter3-Evaluations/eval_results.json.
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

try:
    from azure.ai.evaluation import (
        AzureOpenAIModelConfiguration,
        CoherenceEvaluator,
        F1ScoreEvaluator,
        FluencyEvaluator,
        GroundednessEvaluator,
        RelevanceEvaluator,
        SimilarityEvaluator,
        evaluate,
    )
except ImportError:
    print("❌ azure-ai-evaluation is not installed. Run:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

# The eval SDK builds URLs as {azure_endpoint}/openai/... itself, so strip
# the /openai/v1 suffix used by the OpenAI SDK in Chapters 1-2.
eval_endpoint = endpoint.rstrip("/").removesuffix("/openai/v1")

# Auth: API key if present, otherwise Entra ID via DefaultAzureCredential
# (the eval SDK falls back to DefaultAzureCredential when no key is given —
# requires `az login`, same as Chapter 1).
config_kwargs = {
    "azure_endpoint": eval_endpoint,
    "azure_deployment": deployment_name,
}
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if api_key:
    config_kwargs["api_key"] = api_key
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
if api_version:
    config_kwargs["api_version"] = api_version

model_config = AzureOpenAIModelConfiguration(**config_kwargs)

# --- ANSI colors (same style as previous chapters) ---
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

here = Path(__file__).parent
data_path = here / "eval_data.jsonl"
output_path = here / "eval_results.json"

print(f"{BOLD}{BLUE}Judge model:{RESET} {deployment_name}")
print(f"{BOLD}{BLUE}Dataset:{RESET}     {data_path}")

result = evaluate(
    data=str(data_path),
    evaluators={
        "groundedness": GroundednessEvaluator(model_config),
        "relevance": RelevanceEvaluator(model_config),
        "coherence": CoherenceEvaluator(model_config),
        "fluency": FluencyEvaluator(model_config),
        "similarity": SimilarityEvaluator(model_config),
        "f1_score": F1ScoreEvaluator(),
    },
    output_path=str(output_path),
)

# ---- Report ----
print(f"\n{BOLD}{GREEN}=== Aggregate metrics ==={RESET}")
for metric, value in sorted(result["metrics"].items()):
    print(f"  {YELLOW}{metric:<35}{RESET} {value:.3f}")

print(f"\n{BOLD}{GREEN}=== Row-level detail ==={RESET}")
for i, row in enumerate(result["rows"], start=1):
    query = row.get("inputs.query", "")[:60]
    f1 = row.get("outputs.f1_score.f1_score", 0)
    grounded = row.get("outputs.groundedness.gpt_groundedness", "-")
    relevance = row.get("outputs.relevance.gpt_relevance", "-")
    flag = f"  {BOLD}⚠️  low scores — inspect this row{RESET}" if f1 < 0.5 else ""
    print(f"{DIM}[{i}]{RESET} {query}")
    print(f"     groundedness={grounded}  relevance={relevance}  f1={f1:.2f}{flag}")

print(f"\n{DIM}Full results written to {output_path}{RESET}")
studio_url = result.get("studio_url")
if studio_url:
    print(f"{BOLD}View in Foundry portal:{RESET} {studio_url}")
