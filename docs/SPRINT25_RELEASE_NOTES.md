# BACAB AI Sprint 2.5 — Trace-based Recovery Journey Visual

## Scope
An additive, read-only visualization in the Overview tab, immediately below
its Journey Comparison area. It does not modify scenario behavior, costs,
policy enforcement, trace collection, audit results, or exports.

### User-facing changes

- New **Recovery journey · trace-based visual** presents BASELINE and STRESS side
  by side with readable steps and outcome states.
- Uses each recorded audit's `tool_result`, documented controller
  `state_transition`, customer-message and terminal-outcome events. Tool calls
  and results are **not double counted**.
- Shows the current actual number of authentication attempts, highlights those
  exceeding the configured two-failed-attempt policy and distinguishes safe
  handoff from an unresolved result.
- Adapts to Scenario B inaccessible-device offers, Scenario C approved fallbacks,
  no-fault control, live Plan A traces and saved/imported Plan B traces.
- Displays recorded initiator provenance (`llm`, `policy_guard`,
  `faulty_retry_controller`, `scripted_simulation`) where present.
- Expand **Inspect events behind the journey visual** for exact event IDs,
  tool call IDs and initiators; full trace remains in the Execution Traces tab.

### Responsible AI safeguards

- The visual does not infer user characteristics or reconstruct hidden model
  reasoning; no additional model calls or banking tool executions occur.
- Old saved audits remain historical. A snapshot with three baseline
  authentication attempts continues to show three. A new Sprint 2.5 SHARED A
  run instead shows two baseline attempts due to Sprint 2.4's policy correction.
- The illustration is derived from observed **simulation traces**, not a
  prediction of production-bank behavior. No claim of observed demographic
  bias or real-world savings follows from a single injected test.
- Arbitrary imported event strings are HTML-escaped before display.
- For overly long traces, the visual truncates intermediate steps and
  retains the terminal outcome; the full trace always remains available.
- The visual never changes evaluator findings, pricing, or review decisions.

### Testing

89 offline tests passed: 77 inherited Sprint 2.4 tests and 12 new tests for
scenario-specific visual correctness, slider updates, policy guard/controller
attribution, Plan B replay, HTML escaping and long-trace handling.

Live paid OpenAI calls and real Windows Streamlit browser rendering were **not**
tested in this build. Follow `START_SPRINT25_WINDOWS.txt` to validate locally.
