# Foundry Learning

Hands-on learning project for **Microsoft Foundry** (formerly Azure AI Foundry) — from simple chat calls to tools, evaluations, and responsible AI. Each chapter pairs runnable Python with a module from an official Microsoft Learn path.

## 🎓 Training track

This repo follows the Microsoft Learn path:

**[Develop generative AI apps on Microsoft Foundry](https://learn.microsoft.com/training/paths/develop-generative-ai-apps/)** (AI-3016 · Intermediate · 6 modules)

**Goal:** learn to build, ground, evaluate, and ship a generative-AI app responsibly — by writing code for each concept, not just reading.

### Module ↔ chapter map

| # | MS Learn module | What it teaches | Repo chapter | Status |
|---|---|---|---|---|
| 1 | [Plan and prepare to develop AI solutions on Azure](https://learn.microsoft.com/training/modules/prepare-azure-ai-development/) | Pick services, create a Foundry project, set up your dev environment | [Quick Start](#quick-start-5-minutes) below (project, deployment, `az login`, IAM) | ✅ |
| 2 | [Select, deploy, and evaluate Microsoft Foundry models](https://learn.microsoft.com/training/modules/model-catalog-evaluate/) | Model catalog, deploy to endpoints, evaluate with benchmarks | [Chapter 3 — Evaluations](#chapter-3--evaluations) | ✅ |
| 3 | [Develop a generative AI chat app with Microsoft Foundry](https://learn.microsoft.com/training/modules/foundry-sdk/) | Projects + the Responses API, system messages, parameters | [Chapter 1 — Simple chat call](Chapter1-SimpleChatCall/SimpleChatCallAzure.py) | ✅ |
| 4 | [Develop generative AI apps that use tools](https://learn.microsoft.com/training/modules/use-generative-ai-tools/) | Let the model call tools (function calling, built-in file search) | [Chapter 2 — Tools](Chapter2-Tools/) | ✅ |
| 5 | [Optimize generative AI model performance with Microsoft Foundry](https://learn.microsoft.com/training/modules/optimize-generative-ai-model-performance/) | Prompt engineering, RAG grounding, fine-tuning, when to combine | Chapter 2 (RAG grounding) + [Chapter 3](Chapter3-Evaluations/) (measure before/after) | ✅ |
| 6 | [Implement a responsible generative AI solution](https://learn.microsoft.com/training/modules/responsible-ai-studio/) | Map → measure → mitigate → operate; content filters & safety evaluators | [Chapter 4 — Responsible AI](#chapter-4--responsible-ai) | 🚧 |

> **Certification note:** this path was previously aligned to exam **AI-102**, which Microsoft **retired June 30, 2026**. The skills are current; the badge is not. See [replacement AI credentials](https://techcommunity.microsoft.com/blog/skills-hub-blog/the-ai-job-boom-is-here-are-you-ready-to-showcase-your-skills/4494128).

## Prerequisites

- **Python 3.10+** (this project uses 3.13)
- **Azure CLI** — [install guide](https://learn.microsoft.com/cli/azure/install-azure-cli)
- An **Azure AI Foundry project** — create one at [ai.azure.com](https://ai.azure.com)
- A **deployed model** in your project (e.g., `gpt-4.1`) — deploy under **My assets → Models + endpoints → Deploy model**

## Quick Start (5 minutes)

### 1. Clone & enter the repo

```bash
git clone https://github.com/rayme11/foundry-learning.git
cd foundry-learning
```

### 2. Create & activate the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the values from your Foundry project into the root `.env` file:

```bash
# Required by Chapters 1, 3, 4 (chat + judge + guardrails)
AZURE_OPENAI_ENDPOINT=https://<your-resource>.services.ai.azure.com/openai/v1
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>

# Optional: Chapter 3 model comparison (deploy a second model first)
AZURE_OPENAI_DEPLOYMENT_NAME_2=<second-deployment-name>

# Required by Chapter 4 safety evaluators (project endpoint, not the OpenAI one)
AZURE_AI_PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<project-name>
```

**Where to find these values:**

| Variable | Where to find it |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | [ai.azure.com](https://ai.azure.com) → your project → **Overview** → Endpoint |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Project → **Models + endpoints** → deployment name column |
| `AZURE_AI_PROJECT_ENDPOINT` | Project → **Overview** → project endpoint (contains `/api/projects/`) |

> `.env` is in `.gitignore`, so secrets stay local. Fill in the optional variables as needed per chapter.

### 5. Authenticate with Azure

The scripts use `DefaultAzureCredential` (Microsoft Entra ID). Locally, just run:

```bash
az login
```

Your account needs the **Cognitive Services OpenAI User** role on the Foundry resource:
**Azure portal → your Foundry resource → Access control (IAM) → Add role assignment**

### 6. Run your first chat call

```bash
python Chapter1-SimpleChatCall/SimpleChatCallAzure.py
```

Expected output — a response from your deployed model:

```
answer: [Response(output_text='The capital of France is Paris.', ...)]
```

## Project structure

```
foundry-learning/
├── .env                        # Environment variables (never commit!)
├── .gitignore
├── requirements.txt            # Python dependencies
├── README.md
├── Chapter1-SimpleChatCall/    # Ch. 1: chat completion via OpenAI SDK (module 3)
│   └── SimpleChatCallAzure.py
├── Chapter2-Tools/             # Ch. 2: file-search tool + vector store (modules 4, 5)
│   ├── setup_vector_store.py   #   one-time: upload PDF, create vector store
│   ├── ToolCalling_VectorDB.py #   interactive chat with the file_search tool
│   └── nu_staff_handbook.pdf
├── Chapter3-Evaluations/       # Ch. 3: evaluations & model comparison (modules 2, 5)
│   ├── eval_data.jsonl         #   test dataset (row 5 is wrong on purpose)
│   ├── run_evaluation.py       #   quality evaluators via azure-ai-evaluation
│   └── compare_models.py       #   LLM-as-judge A/B model comparison
└── Chapter4-ResponsibleAI/     # Ch. 4: guardrails & safety (module 6)
    ├── guardrails_demo.py      #   see the content filter block/allow prompts
    └── measure_harms.py        #   content-safety evaluators (hate, sexual, violence, self-harm)
```

## Chapter 3 — Evaluations

```bash
python Chapter3-Evaluations/run_evaluation.py   # quality metrics on a dataset
python Chapter3-Evaluations/compare_models.py   # needs AZURE_OPENAI_DEPLOYMENT_NAME_2
```

`run_evaluation.py` scores each row of `eval_data.jsonl` with built-in evaluators
(groundedness, relevance, coherence, fluency, similarity, F1) using your deployment
as the judge, and writes `eval_results.json`.

`compare_models.py` sends the same prompts to two deployments and has the primary
model judge both answers — set `AZURE_OPENAI_DEPLOYMENT_NAME_2` first.

## Chapter 4 — Responsible AI

Implements module 6's loop: **Map → Measure → Mitigate → Operate**.

```bash
python Chapter4-ResponsibleAI/guardrails_demo.py  # Mitigate: content filter in action
python Chapter4-ResponsibleAI/measure_harms.py    # Measure:  safety evaluators (baseline)
```

- `guardrails_demo.py` sends benign + borderline prompts and reports whether each was
  **answered or blocked** by the deployment's content filter — the exercise's core.
  Adjust thresholds in the portal (deployment → content filter) and re-run to move the boundary.
- `measure_harms.py` runs the **risk & safety evaluators** (0–7 severity for hate/fairness,
  sexual, violence, self-harm) against your Foundry **project** (hosted evaluation service —
  no judge model needed). This is the *baseline* you compare against after applying mitigations.

## How the scripts work

Each chapter loads configuration from the root `.env` automatically using:

```python
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # walks up parent folders to find .env
```

So you can run scripts from any subfolder — no need to `cd` to the root.

**Authentication pattern used** ([SimpleChatCallAzure.py](Chapter1-SimpleChatCall/SimpleChatCallAzure.py)):

```python
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)
client = OpenAI(base_url=endpoint, api_key=token_provider)
```

This gives you keyless auth via Entra ID — tokens refresh automatically.
(Chapter 4's safety evaluators use the project endpoint + `DefaultAzureCredential` directly.)

## Troubleshooting

| Error | Fix |
|---|---|
| `KeyError: 'AZURE_OPENAI_ENDPOINT'` | `.env` missing or variable not set — see step 4 |
| `401 Unauthorized` | Missing IAM role — see step 5 |
| `DefaultAzureCredential failed` | Run `az login` first |
| `404 DeploymentNotFound` | Deployment name mismatch — check **Models + endpoints** in the portal |
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate` |
| Safety evaluators fail to init | Set `AZURE_AI_PROJECT_ENDPOINT` (the `/api/projects/` URL), not the OpenAI endpoint |

## Resources

- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Develop generative AI apps on Microsoft Foundry (training path)](https://learn.microsoft.com/training/paths/develop-generative-ai-apps/)
- [Local evaluation with the Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk)
- [Observability in generative AI (evaluation concepts)](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai)
- [Risk and safety evaluators](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-evaluators/risk-safety-evaluators)
- [OpenAI SDK for Python](https://github.com/openai/openai-python)
- [Azure Identity for Python](https://learn.microsoft.com/python/api/azure-identity/)
