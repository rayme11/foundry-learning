"""
Chapter 3: Side-by-side model comparison (LLM-as-judge)
========================================================
Sends the same set of prompts to TWO deployments and has a judge model
score each answer, so you can compare models on your own workload.

Configuration (.env):
  AZURE_OPENAI_DEPLOYMENT_NAME     — model A and the judge
  AZURE_OPENAI_DEPLOYMENT_NAME_2   — model B (deploy a second model in
                                     Foundry, e.g. gpt-4.1-mini, then set this)

Run:
    python Chapter3-Evaluations/compare_models.py
"""
import json
import os
import sys

from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

load_dotenv(find_dotenv())

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
model_a = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")
model_b = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_2")

if not model_b:
    print("❌ AZURE_OPENAI_DEPLOYMENT_NAME_2 is not set.")
    print("   Deploy a second model in Foundry (Models + endpoints → Deploy model),")
    print("   then add AZURE_OPENAI_DEPLOYMENT_NAME_2=<deployment-name> to .env")
    sys.exit(1)

# Auth: use API key if available, otherwise fall back to Entra ID (requires `az login`)
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if api_key:
    auth = api_key
else:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    auth = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")

client = OpenAI(base_url=endpoint, api_key=auth)

# --- ANSI colors (same style as previous chapters) ---
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

PROMPTS = [
    "Explain the difference between a vector database and a relational database in two sentences.",
    "Write a haiku about continuous integration.",
    "A train travels 120 km in 1.5 hours, then 80 km in 30 minutes. What is its average speed for the whole trip? Show your reasoning.",
]

JUDGE_PROMPT = """You are an impartial evaluator. Score the ANSWER to the QUESTION on:
- correctness (1-5): factually and logically correct
- clarity (1-5): easy to understand
- completeness (1-5): fully addresses the question

Return ONLY a JSON object like:
{"correctness": 5, "clarity": 4, "completeness": 5, "rationale": "one sentence"}

QUESTION: {question}

ANSWER: {answer}"""


def ask(model: str, prompt: str) -> str:
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def judge(question: str, answer: str) -> dict:
    response = client.responses.create(
        model=model_a,
        input=JUDGE_PROMPT.format(question=question, answer=answer),
    )
    try:
        return json.loads(response.output_text)
    except json.JSONDecodeError:
        return {"correctness": 0, "clarity": 0, "completeness": 0, "rationale": "judge returned non-JSON"}


def run_comparison():
    totals = {model_a: {"correctness": 0, "clarity": 0, "completeness": 0},
              model_b: {"correctness": 0, "clarity": 0, "completeness": 0}}

    print(f"{BOLD}{BLUE}Model A:{RESET} {model_a}   {BOLD}{BLUE}Model B:{RESET} {model_b}   {BOLD}{BLUE}Judge:{RESET} {model_a}\n")

    for prompt in PROMPTS:
        print(f"{BOLD}{YELLOW}Q:{RESET} {prompt}")
        for model in (model_a, model_b):
            answer = ask(model, prompt)
            scores = judge(prompt, answer)
            for key in ("correctness", "clarity", "completeness"):
                totals[model][key] += scores[key]
            print(f"  {GREEN}{model}:{RESET} {answer.strip()[:120]}")
            print(f"    {DIM}correctness={scores['correctness']} clarity={scores['clarity']} "
                  f"completeness={scores['completeness']} — {scores['rationale']}{RESET}")
        print()

    print(f"{BOLD}{GREEN}=== Averages (n={len(PROMPTS)}) ==={RESET}")
    for model, t in totals.items():
        n = len(PROMPTS)
        print(f"  {BOLD}{model:<25}{RESET} correctness={t['correctness']/n:.1f}  "
              f"clarity={t['clarity']/n:.1f}  completeness={t['completeness']/n:.1f}")


if __name__ == "__main__":
    run_comparison()
