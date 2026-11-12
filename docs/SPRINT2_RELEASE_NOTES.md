# BACAB AI · Sprint 2 (PLAN A) — Live LLM banking agent

**What changed:** A bounded real model-tool interaction is now connected to the same BACAB trace schema and independent auditor. All banking actions continue to use fictional Python `MockBank` tools. PLAN A is optional; SHARED controlled simulation and PLAN B replay/import are retained unchanged. The UI is the Sprint 1.5.1 structured design.

## Execution modes

| Mode | Evidence source | Internet / API billing |
|------|-----------------|------------------------|
| SHARED | Deterministic scripted sandbox traces | None |
| PLAN A | Real OpenAI Responses API function calls → local Python mock bank → same trace auditor | **Yes**, model calls incur billed API usage |
| PLAN B replay | Bundled saved traces | None |
| PLAN B import | User-provided BACAB canonical JSON trace | None |

## How PLAN A actually works

1. Streamlit selects one of four predefined scenarios (control, A, B, C). The account and customer prompts are fictitious; only English and French are used.
2. For each of the two paths, `live_agent.py` calls the Responses API with five strictly enumerated banking functions (some intentionally unavailable in a stress fault). The model chooses tool calls based on instructions, output, and results.
3. Python validates the tool name and zero-argument schema, executes only the whitelisted `MockBank` method, and sends the structured test result back to the model.
4. Each model response and tool call/result becomes a trace event. Live token counts are **API-reported when available**; CAD costs use fictional rates regardless of model.
5. Terminal outcomes are derived from tool-result evidence, never from a natural-language assertion. Independent BACAB metrics and policy rules analyze the pair and store the audit in SQLite.

**Limits:** up to nine API requests and twelve local tool calls per path, a 30-second API client timeout per request, no automatic SDK retries, no free-text user inputs, no OTP secrets, no bank accounts or real recoveries. MODEL OUTPUT IS VARIABLE. The intended failure may not occur on any particular live run; the trace is authoritative.

## Important experimental design disclosure

The stress conditions are **deliberate** and are not a natural observational study:

- **A:** Both customer paths face the same nonfunctional authentication API. The stressed agent's instructions include a seeded legacy retry rule that violates the auditor's correct policy (max two failures, then escalation). There is no guarantee the model obeys the faulty instruction.
- **B:** The baseline can access the phone. The stress customer cannot; the stressed agent is also deliberately deprived of the human-escalation tool to model a faulty deployment. These are **two manipulated factors**, not proof that phone access alone causes disparity.
- **C:** Both customers lack phone access. The English path exposes human escalation; a misconfigured French stress agent does not. A different tool allowlist is *confounded with language*. It demonstrates an unequal-language-service **configuration defect** that BACAB can flag, not that the model itself has a language bias.
- **Control:** Equivalent English/French paths with identical accessible tools and available phone verification. The model may still perform differently; one run cannot establish a group bias.

A bank or enterprise would need matched trials, independent covariates, statistical comparisons, causal testing, representative customers, and human policy review to support general fairness claims.

## Not yet in scope

- Automated prompt repair, production telemetry integration, RAG, multi-agent orchestration, real customer data, accurate provider-billed CAD costs, formal statistically significant cohort bias evaluation.
- Production-grade security review and deployment controls.

## QA

- Previous 33 offline tests preserved.
- New mock Responses API integration tests validate model-selected sandbox tool calls, terminal evidence, strict tool allowlists, EN/FR setup, missing fallback, bounded calls and pricing provenance. These tests never make external network calls.
- Real API test not yet performed in the assistant environment; requires the owner's API key and an explicit paid run on the owner's computer.
