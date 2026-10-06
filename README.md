# Foundry Learning

Hands-on learning project for **Microsoft Azure AI Foundry** — from simple chat calls to agents, evaluations, and model deployments.

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
# Required by Chapter 1 script
AZURE_OPENAI_ENDPOINT=https://<your-resource>.services.ai.azure.com/openai/v1
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>

# Optional: Chapter 3 model comparison (deploy a second model first)
AZURE_OPENAI_DEPLOYMENT_NAME_2=<second-deployment-name>
```

**Where to find these values:**

| Variable | Where to find it |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | [ai.azure.com](https://ai.azure.com) → your project → **Overview** → Endpoint |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Project → **Models + endpoints** → deployment name column |

> The `.env` file also contains optional variables for API-key auth, service principals, resource management, and embeddings — fill them in as needed for later chapters. `.env` is already in `.gitignore`, so secrets stay local.

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

## Project Structure

```
foundry-learning/
├── .env                        # Environment variables (never commit!)
├── .gitignore
├── requirements.txt            # Python dependencies
├── README.md
├── Chapter1-SimpleChatCall/    # Ch. 1: Basic chat completion via OpenAI SDK
│   └── SimpleChatCallAzure.py
├── Chapter2-Tools/             # Ch. 2: File search tool with a vector store
│   ├── setup_vector_store.py   #   one-time: upload PDF, create vector store
│   └── ToolCalling_VectorDB.py #   interactive chat with file_search tool
└── Chapter3-Evaluations/       # Ch. 3: Evaluations and model comparison
    ├── eval_data.jsonl         #   test dataset (row 5 is wrong on purpose)
    ├── run_evaluation.py       #   built-in evaluators via azure-ai-evaluation
    └── compare_models.py       #   LLM-as-judge model A/B comparison
```

## Chapter 3 — Evaluations

```bash
pip install -r requirements.txt   # adds azure-ai-evaluation
python Chapter3-Evaluations/run_evaluation.py      # quality metrics on a dataset
python Chapter3-Evaluations/compare_models.py      # needs a 2nd deployment
```

`run_evaluation.py` scores each row of `eval_data.jsonl` with built-in
evaluators (groundedness, relevance, coherence, fluency, similarity, F1)
using your deployment as the judge, and writes `eval_results.json`.

`compare_models.py` sends the same prompts to two deployments and has the
primary model judge both answers — set `AZURE_OPENAI_DEPLOYMENT_NAME_2` first.

## How the Scripts Work

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

## Troubleshooting

| Error | Fix |
|---|---|
| `KeyError: 'AZURE_OPENAI_ENDPOINT'` | `.env` missing or variable not set — check step 4 |
| `401 Unauthorized` | Missing IAM role — see step 5 |
| `DefaultAzureCredential failed` | Run `az login` first |
| `404 DeploymentNotFound` | Deployment name mismatch — check **Models + endpoints** in the portal |
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate` |

## What's Next

- **Chapter 4** — Deploying and managing models programmatically (uses `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`)
  - Run: `python Chapter4-ModelDeployment/DeployModels.py`
- **Chapter 5** (future) — Additional advanced topics

## Resources

- [Azure AI Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Local evaluation with the Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk)
- [Observability in generative AI (evaluation concepts)](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai)
- [OpenAI SDK for Python](https://github.com/openai/openai-python)
- [Azure Identity for Python](https://learn.microsoft.com/python/api/azure-identity/)
- [Microsoft Learn: Azure AI Foundry campaigns](https://learn.microsoft.com/en-us/training/modules/prepare-deploy-models/)

## Resources

- [Azure AI Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Local evaluation with the Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk)
- [Observability in generative AI (evaluation concepts)](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-approach-gen-ai)
- [OpenAI SDK for Python](https://github.com/openai/openai-python)
- [Azure Identity for Python](https://learn.microsoft.com/python/api/azure-identity/)
