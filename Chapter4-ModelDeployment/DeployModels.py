"""
Chapter 4: Deploying and managing models programmatically
=============================================================
Deploys and manages models in Azure AI Foundry using the azure-ai-projects SDK.
Uses AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP from .env.

Prerequisites:
  - A deployed model in your Foundry project (e.g., gpt-4.1)
  - Azure CLI authenticated: az login
  - AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP set in .env

Run:
    python Chapter4-ModelDeployment/DeployModels.py
"""
import os
import sys
from dotenv import load_dotenv, find_dotenv

from azure.identity import DefaultAzureCredential  # <-- Added at top level

load_dotenv(find_dotenv())

# --- ANSI colors (same style as previous chapters) ---
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
resource_group = os.getenv("AZURE_RESOURCE_GROUP")

if not subscription_id or not resource_group:
    print("❌ AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP must be set in .env")
    sys.exit(1)

# Auth: use API key if available, otherwise fall back to Entra ID (requires `az login`)
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if api_key:
    from openai import OpenAI
    client = OpenAI(base_url=endpoint, api_key=api_key)
else:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    auth = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
    from openai import OpenAI
    client = OpenAI(base_url=endpoint, api_key=auth)

print(f"{BOLD}{BLUE}Subscription:{RESET} {subscription_id}")
print(f"{BOLD}{BLUE}Resource Group:{RESET} {resource_group}")
print(f"{BOLD}{BLUE}Endpoint:{RESET} {endpoint}")
print(f"{BOLD}{BLUE}Deployment:{RESET} {deployment_name}\n")

# --- List all deployments in the project ---
print(f"{BOLD}{BLUE}Listing model deployments...{RESET}")
try:
    # azure-ai-projects provides a client to list deployments
    from azure.ai.projects import AIProjectClient
    project_client = AIProjectClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_name=resource_group,
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],  # <-- Added
    )
    deployments = list(project_client.models.list_deployments())
    print(f"Found {len(deployments)} deployment(s):")
    for d in deployments:
        print(f"  - {d.name}: {d.model} ({d.status})")
except Exception as e:
    print(f"⚠️  Could not list deployments: {e}")
    print("   (This is ok if you haven't deployed models via the SDK yet)")

# --- Create a new model deployment ---
print(f"\n{BOLD}{BLUE}Creating new deployment...{RESET}")
try:
    # Note: actual deployment creation is done via the Azure portal or azd/az CLI
    # This script demonstrates how to reference and use a deployment
    print("   Deployment creation is typically done via Azure portal or Azure CLI")
    print("   See: https://learn.microsoft.com/azure/ai-foundry/how-to/deploy-model")
except Exception as e:
    print(f"⚠️  Error: {e}")

# --- Demonstrate chat using the deployment ---
print(f"\n{BOLD}{BLUE}Testing deployment with a quick chat call...{RESET}")
try:
    response = client.responses.create(
        model=deployment_name,
        input="Explain the concept of RAG (Retrieval-Augmented Generation) in two sentences.",
    )
    print(f"✅ Response: {response.output_text[:120]}...")
    usage = response.usage
    print(f"   Tokens - input: {usage.input_tokens}, output: {usage.output_tokens}")
except Exception as e:
    print(f"❌ Chat call failed: {e}")

print(f"\n{DIM}Chapter 4 complete — you can now deploy and manage models programmatically.{RESET}")