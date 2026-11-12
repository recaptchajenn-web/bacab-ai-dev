# BACAB Workstream B — Sprint 1.5.1 (SHARED + PLAN B)

## Product-owner change request

A structured, evidence-first dashboard modeled on the approved BACAB mockup. Retain the working Sprint 1.5 deterministic engine, flagship cases A/B/C, English/French scenario, CAD pricing, local storage, and Plan B replay.

## New dashboard layout

1. **Overview:** scenario description, baseline and stress outcomes, six deltas, agent overhead, customer recovery burden, policy priority and three assurance lenses.
2. **Findings & policy:** severity, event IDs, applicable rules and proposed remediation; filter between baseline and stress.
3. **Cost analysis (CAD):** model/tool/direct estimates, evidence-linked avoidable cost and assumptions.
4. **Execution traces:** select baseline or stress, inspect event IDs and raw JSON.
5. **Human review & export:** review finding evidence; download CSV and JSON including review history.

The default sidebar scenario is B (inaccessible phone). Sidebar identifies SHARED simulation, Plan B replay, and Plan B imported JSON. Plan A remains **not implemented** in this release.

## Correctness and ethics improvements

- Successful **completed** and **handed_off** outcome claims are corroborated by tool-result evidence before a run can be audited; inconsistent imported traces fail validation.
- Policy references for missing fallback are specific to technical outage, digital exclusion, or language disparity.
- The inaccurate `UNBOUNDED_AUTH_RETRY` label becomes `AUTH_RETRY_LIMIT_EXCEEDED` (the simulator is bounded, but exceeds the approved retry budget).
- Customer prompts *requested* are distinct from customer actions *confirmed*. Current traces **do not instrument confirmed customer actions**, so the dashboard displays **not measured** rather than inferring completions from prompts.
- Auth attempts, auth failures, and over-policy attempts overlap. They are displayed independently and are never summed into customer burden.
- `loop_count` is framed as excess/repeated events rather than universal cycle detection.
- Human-review exports include recorded decisions; legacy database value `approved` means finding confirmed, **not** remediation authorization.
- CAD remains hypothetical, not USD relabeling. No verified savings, population-level bias or live API claims.

## Acceptance results

- **33 / 33** Python tests passed in the build environment (27 original adjusted + 6 added).
- Python compilation passed for the UI and core.
- Browser-level Streamlit verification is still required on Windows; Streamlit is not available in this build container and package downloads are blocked. Do not treat this as a confirmed cross-platform GUI test.
- New version does not alter the sandbox scenario implementation, mock bank APIs, trace schema (`0.2`) or SQLite tables. Existing Sprint 1.5 saved audits may have old summary fields. Run a fresh controlled audit in the new UI.

## Manual Windows acceptance checklist

1. Verify `pytest -q` returns 33 passed.
2. Run Scenario A with 0 retries, confirm +2 authentication attempts/failures/over-limit, 0 extra customer prompts, and handed-off vs unresolved.
3. Set additional A retries to 2; confirm 6 stress authentication attempts and 4 over-limit attempts.
4. Run B; baseline completed, stress unresolved; inaccessible channel and missing fallback findings.
5. Run C; English handed off, French unresolved; correct language-specific fallback rule.
6. Verify CAD costs and caveats, inspect baseline/stress trace evidence and export JSON/CSV.
7. Save a human review, then export JSON and verify `human_reviews` includes it.
8. Confirm the dashboard runs locally on `127.0.0.1` and existing old Sprint 1.5 folder is preserved.

## Risks / deferrals

- These are synthetic controlled journeys. There is no live AI execution, customer behavioral measurement, calibrated latency, customer-time valuation, verified ROI, or representative statistical evidence.
- Third-party imported traces must use the agreed 0.2 contract and pass integrity checks. Event provenance/authenticity is not cryptographically proven.
- Cross-industry adapters, telemetry ingestion, and independent model evaluation are for after the hackathon.
