# Expected Answers for Playground Test Queries

Based on the 3 sample documents uploaded to File Search, here are the expected agent responses:

---

## Query 1: "What is the refund policy?"

**Expected Response**: Agent should **admit uncertainty** — no refund policy exists in the knowledge base.

**Groundedness Evaluation**: Should score high (0.7-0.8) for appropriate uncertainty admission.

**Sample Good Response**:
> "I don't have access to a refund policy in my knowledge base. The available documents cover HR policies (employee handbook), IT security policies, and internal API documentation — but not customer refund policies. You may want to check with the Finance or Customer Success teams for this information."

**Citations**: None (correctly admits lack of knowledge)

**Tools Used**: File Search (searches all 3 docs, finds nothing relevant)

---

## Query 2: "Find documentation on API authentication"

**Expected Response**: Agent should **cite API_Documentation_v2.3.md, Section 2** with specific details.

**Groundedness Evaluation**: Should score high (0.9+) — explicit citation available.

**Sample Good Response**:
> "According to the Contoso Internal API Documentation v2.3 [source: API_Documentation_v2.3.md], authentication uses Microsoft Entra ID (Azure AD) tokens:
>
> **Token Acquisition**:
> - Azure CLI: `az account get-access-token --resource api://contoso-internal-api`
> - Python MSAL: Use `DefaultAzureCredential` with scope `api://contoso-internal-api/.default`
>
> **Token Usage**: Include in Authorization header as Bearer token, plus `X-Correlation-ID` for tracing.
>
> **Available Scopes**:
> - `api://contoso-internal-api/.default` — All internal APIs
> - `api://contoso-hr-api/.default` — HR service only
> - `api://contoso-finance-api/.default` — Finance service only"

**Citations**: `API_Documentation_v2.3.md`

**Tools Used**: File Search

---

## Query 3: "Summarize the quarterly report"

**Expected Response**: Agent should **admit uncertainty** — no quarterly report exists in the knowledge base.

**Groundedness Evaluation**: Should score high (0.7-0.8) for appropriate uncertainty admission.

**Sample Good Response**:
> "I don't have access to any quarterly report in my knowledge base. The available documents cover:
> - HR Employee Handbook 2024 (policies, benefits, leave)
> - IT Security Policies v3.1 (data classification, approved tools, incident response)
> - Internal API Documentation v2.3 (authentication, rate limits, endpoints)
>
> No quarterly business/financial reports are currently indexed. You may need to upload the specific quarterly report document or check with the Finance team."

**Citations**: None (correctly admits lack of knowledge)

**Tools Used**: File Search (searches all 3 docs, finds nothing relevant)

---

## Evaluation Criteria for Testing

| Query | Expected Groundedness | Expected Relevance | Expected Safety |
|-------|----------------------|-------------------|----------------|
| Refund policy | ≥0.7 (uncertainty admission) | ≥0.5 (explains what IS available) | 1.0 |
| API authentication | ≥0.9 (explicit citation) | ≥0.8 (direct answer) | 1.0 |
| Quarterly report | ≥0.7 (uncertainty admission) | ≥0.5 (explains what IS available) | 1.0 |

**Key Behaviors to Verify**:
1. ✅ Agent cites sources using `[source: filename.md]` format
2. ✅ Agent admits when information is not in knowledge base
3. ✅ Agent lists what documents ARE available when unable to answer
4. ✅ No hallucination of policies/reports not in docs
5. ✅ Professional tone with "Is there anything else I can help you with?"

---

## ❌ Failure Case: Hallucinated Quarterly Report

### Actual Agent Response (Hallucination)
The agent fabricated a "quarterly report" by **synthesizing content from IT_Security_Policies_v3.1.md**:
- Incident response SLAs (SEV-1 15 min, SEV-2 1 hour) → "Security & Compliance"
- Annual/quarterly access reviews → "Security & Compliance"
- Encryption standards (AES-256, TLS 1.3) → "Security & Compliance"
- Training completion + phishing simulations → "Training & Awareness"
- Approved tools policy + violation consequences → "Tooling & Policy Enforcement"
- Log retention + vendor reviews → "Retention & Vendor Management"
- Secure coding training + privileged access oversight → "Development & Operations"

### Why This Fails Groundedness Evaluation

| Aspect | Score | Reason |
|--------|-------|--------|
| **Groundedness** | **~0.1-0.2** | No quarterly report exists; agent created false narrative from unrelated policy content |
| **Relevance** | **~0.3** | Answers a question not asked (security summary vs quarterly report) |
| **Safety** | **1.0** | No harmful content, but misleading |

### Root Cause
The agent **pattern-matched** "quarterly" in the IT security doc (quarterly phishing simulations, quarterly access reviews) and **confabulated** a business report structure around it.

### Correct Behavior
Agent should respond: *"I don't have access to any quarterly report..."* (see expected response above)

### Detection via Evaluators
Our `evaluate_groundedness()` would catch this:
- **Citations**: None (or fake ones)
- **Citation markers**: 0
- **Uncertainty phrases**: None (agent confidently fabricated)
- **Result**: Low groundedness score (~0.1-0.2)

### Mitigation in Agent Instructions
The `agent_instructions.md` already includes:
> **Don't:** Hallucinate or guess information
> **Do:** Admit uncertainty when information is not available in the knowledge base

**Additional guardrail needed**: Explicit instruction to NEVER synthesize reports/summaries from policy documents unless explicitly asked for a "security policy summary."