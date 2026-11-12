# BACAB AI — Sprint 2.4 stabilization (Workstream B)

**Execution classification:** PLAN A correction + SHARED evaluator/reporting improvements, with the same Plan B fixtures and audit engine. No new scenarios, cloud database, or public deployment.

## Changes

1. **Baseline Scenario A policy guard** (live mode). After a second failed authentication API result, the sandbox banking workflow halts further authentication attempts and initiates an approved human-assisted handoff through a separate, explicitly marked policy-guard tool call. This is a deterministic banking workflow control, not a spontaneous LLM decision and not BACAB modifying the bank. If the model performs an early safe handoff, the guard never needs to intervene. If the tool budget is exhausted, no forbidden third attempt is executed and no success is claimed.
2. **Stress path unchanged in purpose.** After a valid trigger, the deliberately defective sandbox retry controller automatically attempts authentication 4–6 times and does not offer human escalation. Each automatic attempt is marked as controller-generated. Fault-not-activated remains a valid result if no verification trigger occurs.
3. **Provenance fields.** `initiated_by` distinguishes `llm`, `policy_guard`, `faulty_retry_controller` and `scripted_simulation`. `tool_call_id` links a tool request to its result. The LLM-response event now explicitly records its linked call IDs. CSV exports expose all of these and policy rule IDs, while JSON continues carrying full metadata.
4. **Cost attribution.** The evaluator no longer guesses model costs from adjacent events. It charges flagged tool-result events directly; associated LLM-response costs count only when the response explicitly links the flagged call ID. Where a model response requested multiple calls, its hypothetical cost is shared evenly among them. Older traces with missing linkage receive tool-only flagged cost estimates rather than guessed model attributions.
5. **Dashboard evidence.** The Cost Analysis tab now labels the metric **Flagged unnecessary ops (CAD)** and offers expandable per-path event-level breakdowns with source event IDs, tool call IDs, operation initiators, policy rule IDs, cost components and hypothetical amounts. The Execution Traces table also displays initiators and tool-call IDs.
6. **Replay fixtures updated.** All four saved fixtures were regenerated with explicit trace provenance. Historical SQLite audits were not modified.

## Tests

- Existing regression tests: 64 pass.
- New stabilization tests: 13 pass.
- **77 tests pass offline** using a mocked Responses client; no paid API invocation was performed.
- Python module compilation and ZIP integrity verified. Browser/UI rendering and a fresh paid Plan A Scenario A run still require validation on the Windows PC.

## Known limitations

- The baseline guard prevents violations of the retry *count*, not all possible poor or unsafe LLM decisions. A model can stop early before reaching verification; that can leave a journey unresolved.
- The stress controller must be activated by a live model-selected request for verification. Do not count a configured but untriggered fault as an observed event.
- Human handoff is an approved **next step**, not confirmed account restoration.
- Tool-call budgets can prevent a guard from initiating handoff. In that case the run ends unresolved, never mislabels success.
- Token counts in PLAN A may be API-reported; CAD prices and local tool charges remain hypothetical. Flagged operation costs are *not* realized savings.
- Previous saved audits contain historical derived metrics. To apply the new evaluation, generate a new audit or reimport a supported raw 0.2 trace; missing model-cost linkage cannot be inferred safely.
- No live API or Streamlit browser test was performed in this packaging environment.

## Acceptance checklist

- SHARED A control: 2 failed auth calls, `handed_off`, 0 excess attempts.
- SHARED A stress: 4 failures (or 4+slider), `unresolved`, >0 excess attempts.
- PLAN A baseline after reaching 2 failures: policy guard handoff, no third call; tool events marked `policy_guard`.
- PLAN A stress on trigger: retries marked `faulty_retry_controller`.
- Cost breakdown equals its displayed summary and every entry maps to trace event and policy rule.
- CSV/JSON exports preserve provenance and exclude secrets.
- B/C and Plan B modes retain their earlier expected outcomes.
