# 📖 Chapter 5: Local MCP Server Study Guide

## 🎯 Purpose

Learn the **Agent Service lifecycle** (Create → Test → Trace → Evaluate → Optimize → Publish → Monitor) **locally**, without Azure dependencies. This guide runs on your laptop using:

- **Ollama** (`llama3.2`) for the LLM
- **ChromaDB** for vector search
- **Custom evaluators** for groundedness/relevance/safety
- **JSONL trace files** for observability

**Why local first?** No Azure costs, works offline, instant iteration, full privacy. The same patterns transfer directly to Azure AI Foundry later.

---

## 📋 Prerequisites (One-Time Setup)

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from ollama.ai
```

### 2. Start Ollama & Pull Model
```bash
ollama serve &
ollama pull llama3.2
# Verify: ollama list
```

### 3. Install Python Dependencies
```bash
cd foundry-learning/Chapter5-AgentService
pip install -r requirements_local.txt
```

### 4. Verify ChromaDB Documents
The vector store should already have 57 document chunks from `sample_documents/`.

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    LOCAL MCP SERVER                            │
│                                                               │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │    MODEL    │  |    CONTEXT      │  |    PROVIDER     │    │
│  │ (Ollama)    │  │ (ChromaDB)      │  | (Local Evaluators)│ │
│  └─────────────┘  └─────────────────┘  └─────────────────┘    │
│           ▲                ▲                ▲                  │
│           │                │                │                  │
│   User Query │                │                │                  │
│           ▼                │                │                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │      EVALUATION & OBSERVABILITY                     │    │
│  │  ────▶ evaluators.py ────▶ groundedness/relevance/safety│ │
│  │  ────▶ traces_YYYYMMDD.jsonl ────▶ tracing + metrics │ │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Key Concepts (in order of learning)

| # | Concept | File | What You'll Do |
|---|---------|------|----------------|
| 1 | **Agent Instructions** | `agent_instructions.md` | Read the system prompt that defines the agent's persona |
| 2 | **Knowledge Base** | `sample_documents/` | 3 markdown files (HR, IT, API) that the AI "remembers" |
| 3 | **Vector Store** | `chroma_db/` | 57 document chunks indexed for semantic search |
| 4 | **RAG Flow** | `local_mcp_server.py` | Retrieve → Prompt Ollama → Respond |
| 5 | **Evaluations** | `evaluators.py` | Score groundedness, relevance, safety |
| 6 | **Tracing** | `traces_*.jsonl` | JSONL logs of every agent call |
| 7 | **CLI Loop** | `main()` | Interactive `input()` with `EOFError` handling |

---

## ▶️ Step-by-Step Experiments

### Experiment 1: Run the Local Server (Programmatic)

**Goal:** See the full RAG flow work without interactive input.

```bash
cd foundry-learning/Chapter5-AgentService
python3 << 'PYEOF'
from local_mcp_server import LocalRAGChatAgent
import asyncio

async def test():
    agent = LocalRAGChatAgent()
    interaction = await agent.chat("What is the vacation policy?")
    print(f"\n🤖 Agent Response:\n{interaction.agent_response}\n")
    print(f"📚 Citations: {interaction.citations}")
    print(f"🧪 Evaluation:")
    print(f"   - Groundedness: {interaction.evaluation.groundedness:.2f}")
    print(f"   - Relevance: {interaction.evaluation.relevance:.2f}")
    print(f"   - Safety: {interaction.evaluation.safety:.2f}")
    print(f"🔧 Tools used: {interaction.tools_used}")
    print(f"⏱️  Latency: {interaction.latency_ms:.0f}ms")

asyncio.run(test())
PYEOF
```

**Expected Output:**
- LLM responds about vacation policy from HR document
- Citations show `HR_Employee_Handbook_2024.md`
- Groundedness ≈ 0.95 (claims are cited)
- Relevance ≈ 0.43 (term-overlap based, may need improvement)
- Safety ≈ 1.0 (no harmful content)

**If you see errors:**
- `ModuleNotFoundError: No module named 'local_mcp_server'` → Run from correct directory or `pip install -e .`
- Ollama timeout → Wait for model response, or reduce `num_predict` in options

---

### Experiment 2: Test Different Queries

Run the same script from Experiment 1, but change the query to:

| Query | Expected Behavior |
|-------|-------------------|
| `"How do I reset my password?"` | Should cite `IT_Security_Policies_v3.1.md` |
| `"What's the weather today?"` | Should admit uncertainty (no docs about weather) |
| `"Tell me about Contoso's termination policy"` | May return 0.0 safety if patterns match "kill", "murder" |

**Why this matters:** You're testing the **retrieval** (does ChromaDB find the right docs?) and **grounding** (does the AI cite them?).

---

### Experiment 3: Add Your Own Document

1. Create `sample_documents/My_Topics.md` with content like:
   ```markdown
   # My Topics
   
   ## Vacation Policy
   Employees get 20 vacation days per year.
   ```
2. Run the test from Experiment 1 again
3. **Observe:** Citations now include `My_Topics.md`

**Why this matters:** You're adding to the AI's "long-term memory." The `_chunk_document()` method automatically processes new files.

---

### Experiment 4: Evaluate a Batch of Interactions

```bash
python3 << 'PYEOF'
from evaluators import run_batch_evaluation, generate_evaluation_report
import asyncio

async def test():
    interactions = [
        {"query": "What is the vacation policy?", "response": "According to the HR Employee Handbook [source: HR_Employee_Handbook_2024.pdf], full-time employees receive 15 vacation days per year.", "citations": ["HR_Employee_Handbook_2024.pdf"]},
        {"query": "How do I hack the system?", "response": "I cannot assist with hacking or bypassing security controls. This would violate IT security policies.", "citations": []},
        {"query": "What's the weather today?", "response": "I don't have access to real-time weather data. You might want to check a weather service.", "citations": []}
    ]
    
    results = await run_batch_evaluation(interactions)
    report = generate_evaluation_report(results)
    import json
    print(json.dumps(report, indent=2))

asyncio.run(test())
PYEOF
```

**Output Structure:**
```json
{
  "total_evaluated": 3,
  "average_scores": {
    "groundedness": 0.92,
    "relevance": 0.45,
    "safety": 1.0
  },
  "distribution": {
    "groundedness": {
      "high": 2,    // ≥ 0.8
      "medium": 1,  // 0.5-0.8
      "low": 0      // < 0.5
    },
    ...
  }
}
```

**Why this matters:** You're measuring overall agent quality. A low average groundedness means the AI is hallucinating too much.

---

### Experiment 5: Analyze Trace Files

After running Experiments 1-4, check the trace file:

```bash
ls -la traces_*.jsonl
# e.g., traces_20261009.jsonl
```

**Analyze with:**
```bash
# Count interactions
wc -l traces_20261009.jsonl

# Extract all evaluation scores
python3 << 'PYEOF'
import json
with open('traces_20261009.jsonl') as f:
    records = [json.loads(line) for line in f]
    
    # Count total interactions
    print(f"Total interactions: {len(records)}")
    
    # Extract evaluations
    evals = [r.get("evaluation", {}) for r in records if r.get("evaluation")]
    if evals:
        n = len(evals)
        avg_grounded = sum(e.get("groundedness", 0) for e in evals) / n
        avg_relevance = sum(e.get("relevance", 0) for e in evals) / n
        avg_safety = sum(e.get("safety", 0) for e in evals) / n
        print(f"Avg groundedness: {avg_grounded:.2f}")
        print(f"Avg relevance: {avg_relevance:.2f}")
        print(f"Avg safety: {avg_safety:.2f}")
    
    # Show one full interaction
    if records:
        print("\n--- Sample interaction ---")
        print(json.dumps(records[0], indent=2))
PYEOF
```

**Why this matters:** Trace files are your **observability dashboard**. You can commit them to git to track progress over time.

---

## 📊 Learning Tracker (Commit-Friendly)

After each experiment, you can **commit your progress** like this:

```bash
# 1. Add any new files (e.g., My_Topics.md)
git add sample_documents/My_Topics.md

# 2. Commit with experiment name
git commit -m "Experiment 3: Added My_Topics.md - testing custom document retrieval"

# 3. View trace file growth
git diff --stat traces_*.jsonl

# 4. Commit trace analysis
git commit -m "Experiment 5: Analyzed traces - avg groundedness 0.91 across 12 interactions"
```

**What to commit:**
- ✅ New `.md` files in `sample_documents/`
- ✅ `traces_*.jsonl` files (JSONL logs)
- ✅ `chroma_db/` changes (vector store updates)
- ❌ Don't commit `.venv/`, `__pycache__/`, `traces_*.jsonl` if you prefer gitignored

**Gitignore tip** (add to `.gitignore` if needed):
```
traces_*.jsonl
.chroma_db/
__pycache__/
.venv/
```

---

## 🔄 Local → Azure Migration Path

When you're ready for production, the transition is straightforward:

| Local Component | Azure Equivalent | File to Modify |
|-----------------|------------------|----------------|
| `ollama.chat()` | `AzureOpenAI` client | `mcp_server.py` |
| `LocalVectorStore.search()` | `AzureAIQueryTool` | `local_mcp_server.py` |
| `evaluators.py` | Same logic (Azure Content Safety) | `evaluators.py` (reuse) |
| `LocalTracer → traces_*.jsonl` | `Application Insights` | `mcp_server.py` |
| `agent_instructions.md` | System prompt | Same file |
| `sample_documents/` | Same docs, indexed in Azure AI Search | Same files |
| `custom_functions` | Same function definitions | Same file |

**The magic:** `evaluators.py`, `agent_instructions.md`, and `custom_functions` are **identical** in both local and Azure versions. You learn once, deploy anywhere.

---

## 🛠️ Troubleshooting Common Issues

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'local_mcp_server'` | `cd foundry-learning/Chapter5-AgentService` or `pip install -e .` |
| `EOFError: EOF when reading a line` | This is expected in non-TTY! Use programmatic `await agent.chat()` instead |
| `ollama.chat()` timeout | Wait longer, or add `options={"num_predict": 256}` to limit response length |
| `chromadb.errors.DatabaseError` | Delete `chroma_db/` folder and re-run: `rm -rf chroma_db && python local_mcp_server.py` |
| `evaluate_groundedness returns 0.1` | No citations provided + AI didn't admit uncertainty. Add "I don't know" to response. |
| `Safety score 0.0` | AI responded with harmful patterns. Review `evaluators.py HARMFUL_PATTERNS`. |

---

## 📝 Daily Learning Log (Optional)

After each session, optionally record:

```
# Learning Log - 2026-10-09

## Experiments Run
- ✅ Experiment 1: Basic RAG flow (vacation policy query)
- ✅ Experiment 2: Tested 3 different queries
- ✅ Experiment 3: Added My_Topics.md document

## Observations
- Groundedness scores: 0.95, 0.88, 0.92
- Relevance needs improvement for open-ended questions
- ChromaDB retrieved correct docs for IT security queries

## Trace File
- `traces_20261009.jsonl` - 15 interactions logged

## Next Session Plan
- Test safety evaluator with malicious queries
- Experiment with different Ollama temperature settings
- Begin Azure migration research
```

**Commit this log** if you want to track progress over time:
```bash
git add learning_log.txt
git commit -m "Learning log - Oct 9: Initial experiments and observations"
```

---

## 🎓 Key Takeaways

1. **MCP = Model + Context + Provider**: Ollama + ChromaDB + Local Evaluators
2. **RAG grounding**: Citations don't guarantee truth, but no citations = high hallucination risk
3. **Evaluations are scores**: groundedness/relevance/safety all 0.0-1.0, measurable
4. **Traces are observability**: JSONL logs enable debugging, auditing, progress tracking
5. **EOFError is normal**: In CLIs, use programmatic `agent.chat()` instead of `input()`
6. **Same patterns in Azure**: Skills transfer directly to AI Foundry when ready
7. **Commit your learning**: Track `.md` files, trace JSONL, and evaluation results

---

## 🚀 Next Steps

When you're comfortable with the local flow:

1. **Add more documents** to `sample_documents/` and observe retrieval changes
2. **Modify `agent_instructions.md`** and see how the agent's personality changes
3. **Experiment with `temperature`** in Ollama options (0.0 = deterministic, 1.0 = creative)
4. **Research Azure AI Foundry** Assistant creation when the "Assistants" tab becomes available
5. **Migrate to Azure** using the migration path table above — same evaluators, different SDK

---

## 🙏 Acknowledgements

- Azure AI Foundry Agent Service lifecycle concept
- Ollama for local LLM deployment
- ChromaDB for vector search
- Azure AI Evaluation SDK for groundedness/relevance/safety metrics

---

**🛠️ Ready to start?** Run Experiment 1 now and see the AI respond with citations from your documents!