# BACAB AI — Sprint 2.2: Correct Live Audit/Scenario Identity

## Root cause

The Streamlit dashboard retained the last successfully completed report in
`st.session_state['audit']` after the user changed stress scenario or execution
mode. It also retained that report if a new PLAN A live run failed partway through.
As a result, selecting B could leave the earlier C result visible even though
OpenAI had billed partial calls. The live Python runner already received the
selected scenario; this was primarily a presentation/state-integrity defect.

## Corrections

1. Invalidate current report when the non-secret run configuration changes:
   execution mode, scenario, retry slider, live model, or model-call limit.
2. Clear the previous report BEFORE any new run (including a paid live run).
3. Reject new audit results whose declared scenario does not match selection,
   or whose mode is synthetic when PLAN A was chosen, BEFORE saving/displaying.
4. When a live run fails, show a persistent safe diagnostic indicating whether
   the baseline or stress path failed; never expose provider response bodies or
   API secrets. An incomplete run never yields a new paired audit report.
5. Display explicit report identity on every completed report: actual scenario,
   source, pair ID, and newly completed vs. loaded from Saved History.
6. Retain history mode intentionally, but label it SAVED HISTORY prominently.
7. Add six new offline regression tests. Prior package: 50 tests; now 56 tests.

## Verification performed

- Python source compilation: passed.
- Automated tests: **56/56 passed** (offline, using mocked Responses API).
- ZIP integrity and checksums: checked in release packaging.
- Actual Streamlit browser layout and paid model calls: **NOT** tested here;
  must be verified on the user's Windows machine.

## Windows manual acceptance procedure

1. In SHARED, select B and run. Report must show B and `sandbox_synthetic`.
2. Select C, **do not press Run**. The B report must disappear, replaced by a
   notice to run the selected scenario (not the old result).
3. Change back to B, select PLAN A, enter your key privately, authorize paid
   calls, press Run. If both paths finish, the report must show B and
   `source=live_openai` in REPORT IDENTITY. If API execution fails, the page
   must show an explicit failure, not the old C result.
4. Select A, move its retry slider, do not run: old B report must disappear.
5. Open Saved History and select a C report: label must clearly state SAVED
   HISTORY, and the report identity should show C and the actual source.
6. Never include the API key in screenshots, logs or shared exports.

## Limitations

This update addresses stale results and run diagnostics; it does not guarantee
that the live LLM will choose the tool that activates Scenario A's intentionally
faulty retry controller. If not activated, BACAB should report that truthfully.
Recorded live calls may incur charges even if a pair fails halfway through.
