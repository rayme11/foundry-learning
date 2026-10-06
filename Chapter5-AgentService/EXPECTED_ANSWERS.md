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
3. ✅ No hallucination of policies/reports not in docs
4. ✅ Professional tone with "Is there anything else I can help you with?"