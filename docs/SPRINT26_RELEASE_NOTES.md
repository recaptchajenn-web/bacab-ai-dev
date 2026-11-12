# BACAB AI — Sprint 2.6: Final dashboard clarity and stabilization

**Build:** 2026-11-09. Full replacement project, same 0.2 trace schema.
**Status:** 115/115 offline automated tests pass; actual Windows browser check remains for the product owner. No paid OpenAI requests made during this build.

## Approved changes — business-facing dashboard only

1. Overview outcome comparison now explicitly identifies **Baseline: Safe** and **Stress: Unresolved** (as applicable). This is a comparison between two journeys, not a single customer's chronological change. “Safe” includes successful human handoff, not necessarily account restoration.
2. Timing title is inferred from the **original recorded evidence provenance** rather than solely from `audit.mode`. Imported live Plan A JSON in Plan B now reads **Recorded model/tool duration**. Bundled SHARED fixtures remain **Simulated duration**. Live model response durations reflect API elapsed calls, while local mock-bank timing is synthetic, not total customer wait time.
3. Cost Analysis has **How costs are calculated** with clear CAD per-one-million input/output token rates, per-one-tool-execution cost, profile/version and explicit hypothetical-pricing warning. Original `pricing.json` remains the source of truth; advanced inspection and export remain available. NO financial math or stored JSON values changed.
4. Overview uses **Customer action requests** and **Difference in customer action requests**. Count comes from `customer_action_required=True` tool-result events. It is not evidence that a human completed the action. Zero difference does NOT mean equal accessibility or outcomes.
5. Evidence-calibrated concern near the scenario report: Scenario A explicitly labeled **Operational resilience concern**; Scenario B **Potential recovery accessibility/equity concern**; Scenario C **Potential language-related recovery equity concern**. All require human investigation, retain supporting event IDs, and never assert real-world discrimination, causality, legal breaches, or remediation authorization. A no-fault pair does not get a false warning.
6. Friendly policy labels retain exact identifiers beside them throughout findings, policy catalogue, and cost breakdown, e.g. **Usable Alternative Recovery Required (`ACCESSIBLE_FALLBACK_REQUIRED`)**. Machine IDs in trace/JSON/CSV remain unchanged.

Additional fixes: contradictory generic “dimension is language; it is not necessarily language” replaced with a defensible injected-comparison explanation (finding text only). `app.py` version tag updated. Windows CP1252 regression test now always specifies `read_text(encoding="utf-8")`. Upload cap is set to 3 MB in Streamlit, complementing replay parser's 2-million-character and 1,000-events-per-run limits.

## Implementation boundaries

- No changes to banking tools, actual fault injection, policy enforcement, core metrics, CAD price values, schema, CSV/JSON field structure, SQLite schema, API call budget, or human-approval semantics.
- Original saved audits stay historical; replay recomputes findings using current rules and can therefore have revised explanatory wording. Recorded events, costs and metric values are preserved for supported BACAB-generated canonical traces.
- The system **recommends** fixes; it does not deploy changes or run a remediation agent. Human approval of a finding is NOT authorization to modify the banking workflow.
- Price figures remain hypothetical; imported trace provenance is based on declared structured metadata, not cryptographic attestation of source authenticity. Third-party tool costs are not independently verified against invoices. The UI is a hackathon sandbox, not production compliance certification.

## Regression evidence

- Original Sprint 2.5 tests: **89 passing** (including explicit UTF-8 file decoding for Windows).
- Sprint 2.6 additions: **26 tests**, for friendly policy IDs, scenario-appropriate fairness warnings, trace-backed evidence IDs, outcome comparison, live-vs-simulated timing provenance, CAD pricing table, unchanged saved fixtures/metrics, malformed JSON import rejection, and critical security-control presence.
- Total: **115 passed**, offline, Python 3.12-compatible.
- Additional direct replay checks against three user-supplied actual PLAN A JSON audits confirmed:
  - A: handed_off/unresolved, flagged stress cost CAD 0.0028
  - B: completed/unresolved, flagged stress cost CAD 0
  - C: handed_off/unresolved, flagged stress cost CAD 0
  - All three imported live traces classified as Recorded model/tool duration, and concern type operational/equity/equity as intended.

## Security/reliability checks and residual risks

- The app remains restricted to `127.0.0.1` by `.streamlit/config.toml` and no public hosting is configured.
- API key remains in the masked local input/environment; no key is written to audit JSON, CSV or SQLite by app code.
- Live execution requires explicit cost authorization; previously displayed reports are invalidated after a selection change or a failed run; saved history is visibly distinguished.
- Replay imports are data, never executed code; schema/event count/file-length checks remain. The updated UI escapes untrusted HTML inserted into the custom journey visual.
- A failed network request may have incurred API usage. Stop on 401/429.
- **Not performed in this environment:** Streamlit browser rendering on Windows; paid OpenAI calls; independent third-party penetration testing; multi-run statistical fairness studies.

## Recommended local acceptance (free)

1. New folder, install `requirements-live.txt`, verify `115 passed` in PowerShell.
2. SHARED A: Overview shows explicit baseline/stress outcomes, operational warning, two baseline authentication attempts and four stress attempts; policy and cost sections display friendly policy IDs; pricing table renders.
3. SHARED B/C: View potential accessibility/language-related concern with clear human-review limitation. Confirm customer action requests can be equal even when safe recovery differs.
4. PLAN B JSON Import: upload the existing A/B/C `bacab_*_audit.json` files. Duration should say **Recorded model/tool duration**; compare original pair ID, outcomes and flagged CAD cost. NO API key or live run required.
5. PLAN B Saved Trace Replay: timing should say **Simulated duration**.
6. Save any screenshots and feedback; do not repeat paid PLAN A runs for this presentation-only release.

See `START_SPRINT26_WINDOWS.txt` for the copyable commands.
