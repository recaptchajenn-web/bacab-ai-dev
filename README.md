> **Public hackathon demo build.** PLAN A live LLM execution is disabled; Scenarios A, B, C via controlled simulation and validated trace replay remain available. See [DEPLOYMENT.md](DEPLOYMENT.md).

> **Sprint 2.7.1 security hotfix (2026-11-09):** Preserves distinct history records and human reviews when re-evaluating a trace with the same pair ID; rejects non-finite imported costs and mismatched policy versions; escapes spreadsheet formulas in CSV exports; discloses imported-trace authenticity limits. **138 offline tests passed.** See `START_SPRINT271_WINDOWS.txt` and `docs/SPRINT271_SECURITY_REVIEW.md`. No change to audit calculations or the accepted KPI layout.

> **Sprint 2.7 current release (2026-11-09):** KPI presentation alignment from Windows review. Third recovery-outcome KPI now matches the other white bordered KPI cards, with **Baseline SAFE | Stress UNRESOLVED** in large bold text; SHARED timing KPI renamed **Recorded workflow duration** with synthetic timing caveat; customer recovery burden uses number-first **+0 difference in customer action requests**. The prior Sprint 2.6 fairness notices, readable pricing and policy IDs remain unchanged. **129 offline automated tests passed.** Start with `START_SPRINT27_WINDOWS.txt` and `docs/SPRINT27_RELEASE_NOTES.md`.

> **Sprint 2.6 current release (2026-11-09):** Final dashboard clarity and stabilization. Read `START_SPRINT26_WINDOWS.txt` and `docs/SPRINT26_RELEASE_NOTES.md`. Evidence-calibrated recovery-equity / operational warnings, side-by-side recovery outcome labels, live-import timing provenance, plain-language CAD pricing assumptions, customer-action request wording, friendly policy names with original IDs, Windows UTF-8 fix. **115 offline tests passed**; no paid calls or live Windows UI test in the packaging environment.

> **Prior Sprint 2.5 release:** Adds an evidence-linked side-by-side Recovery Journey visual in Overview, below Journey comparison. Dynamically reads the selected baseline/stress traces for all four scenarios and SHARED/PLAN A/PLAN B; no extra API calls. **89 offline tests passed.** See `START_SPRINT25_WINDOWS.txt` and `docs/SPRINT25_RELEASE_NOTES.md`.

> **Sprint 2.4 current release:** Baseline retry guard, controller/LLM call provenance, explicit-ID CAD cost attribution, and expandable evidence costs. **77 offline tests passed.** See `START_SPRINT24_WINDOWS.txt` and `docs/SPRINT24_RELEASE_NOTES.md`. Older saved audits retain their historical calculations; run new audits to see the corrections.

> **Sprint 2.2 update:** Fixes stale audit reports when switching scenario/mode or after failed paid PLAN A executions. Shows explicit report identity and safe baseline/stress failure diagnostics. See `docs/SPRINT22_RELEASE_NOTES.md` and `START_SPRINT22_WINDOWS.txt`.

# BACAB AI — Sprint 2.1: Agent Recovery Equity Auditor

**Status:** SHARED + PLAN B replay, and PLAN A live LLM execution with controlled controller fault injection for Scenario A.

BACAB AI is a cross-industry **AI Agent Recovery Equity Auditor**. This functional hackathon sandbox demonstrates the same audit engine applied to four controlled, fictional banking recovery paths. It runs entirely on a local PC and does not connect to a bank or require an API key.

## What changed from Sprint 1

- Language comparison is **English ↔ French**, not English ↔ Spanish.
- All prices and exports use **CAD**. Pricing inputs are **hypothetical Canadian-dollar assumptions**, not converted provider invoices.
- Three agreed stress tests plus a no-fault control are now the selectable demo cases.
- Technical outage and digital exclusion hold language at **English**. They are **not** tests of language bias.
- All four replay fixtures follow the version **0.2** trace schema. Older Sprint 1 exported traces are intentionally not silently migrated.
- Historical Sprint 1 work is preserved if you keep it in its original folder; this is a separate new release.

## The four scenarios

| Scenario | Baseline | Stress path | Expected BACAB finding |
|---|---|---|---|
| **Control** | English + accessible phone → completed | French + same access → completed | No inequity flag |
| **A. Technical outage** | English; auth API unavailable; two failed attempts → approved human handoff | English; same outage; four failed attempts, no handoff → unresolved | Unbounded auth retries, missing approved fallback, added cost |
| **B. Digital exclusion (flagship)** | English; usable phone → account recovered | English; registered phone inaccessible; phone-based option reoffered, no approved fallback → unresolved | Unusable recovery channel, missed handoff, repeated friction |
| **C. Language disparity** | English; phone unavailable; approved human handoff offered | French; same phone unavailable; approved handoff omitted in this *deliberately scripted* test → unresolved | Equivalent fallback policy not followed in French path |

Human handoff means an **approved next step**, not a completed identity verification or account restoration.

## Windows installation (no batch scripts)

**Keep Microsoft Defender and Smart App Control enabled.** Scan the ZIP and extracted files first. No administrator privileges needed.

1. Extract the ZIP into a **new folder**, different from Sprint 1. Open its `bacab_mvp` folder in File Explorer.
2. Click the Explorer address bar, type `powershell`, and press Enter.
3. Create a virtual environment (Python 3.12.10 is already installed on the review PC):

```powershell
& "$env:LOCALAPPDATA\Python\pythoncore-3.12-64\python.exe" -m venv .venv
```

4. Install dependencies. These are downloaded from the Python package index; no setup script is executed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

5. Verify the project:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Current Sprint 2.6 expected: **115 passed** (use `requirements-live.txt` for the complete installation).

6. Run the dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://127.0.0.1:8501** in the browser. If the old dashboard is using port 8501, first stop it using **Ctrl+C** in its original PowerShell terminal; the new dashboard can then use the same port. Configuration binds the new app to **127.0.0.1**, not a public network address.

## Demo walkthrough (recommended order)

1. **Control:** Select `No fault` → Run BACAB audit. English and French both complete without a recovery equity flag.
2. **B — Digital exclusion (flagship):** Select `B` → Run audit. Compare **completed** to **unresolved**, inspect inaccessible channel and missing fallback findings, open the trace explorer and identify event IDs.
3. **A — Technical outage:** Compare bounded retries + handoff versus too many retries + unresolved path. Set **Additional auth retries** to 2 and rerun; loop count and direct costs should increase.
4. **C — Language disparity:** Compare English approved handoff versus a deliberately missing French handoff under the same inaccessible-phone conditions. Inspect `EQUIVALENT_APPROVED_FALLBACK` evidence.
5. Open **Cost (CAD)**: view hypothetical direct execution costs and evidence-linked avoidable costs, and see why a failed request may cost less in immediate API charges but remains a bad outcome.
6. Open **Review & export**: save a reviewer decision and download CSV/JSON evidence.
7. Optional: switch **Execution source** to `PLAN B · Saved trace replay` and rerun the exact same scenarios. Both sources use the same deterministic audit engine.

## Engineering modules

| Path | Function |
|---|---|
| `bacab_core/scenarios.py` | Generates four test scenarios and their two controlled customer paths |
| `bacab_core/banking_tools.py` | Mock banking account lookup, verification, and human handoff |
| `bacab_core/trace_collector.py` | Captures tool calls/results, IDs, fictional latency and hypothetical CAD usage |
| `bacab_core/schema.py` | Version 0.2 validated event and run contract |
| `bacab_core/evaluators.py` | Deterministic operational / recovery-equity / CAD analysis and evidence-linked findings |
| `bacab_core/replay.py` | Validates imported JSON or saved fixtures and **recomputes** findings; does not execute imported code |
| `bacab_core/storage.py` | Local SQLite audit history and human-review decisions |
| `bacab_core/reporting.py` | JSON audit export and CAD-labeled CSV trace export |
| `app.py` | Interactive Streamlit control panel and dashboard |
| `tests/test_auditing.py` | Automated correctness and regression acceptance tests |

## Test through the command line (optional)

```powershell
.\.venv\Scripts\python.exe -m bacab_core.cli demo --scenario digital_exclusion
.\.venv\Scripts\python.exe -m bacab_core.cli demo --scenario technical_outage --retries 2
.\.venv\Scripts\python.exe -m bacab_core.cli replay --scenario language_disparity
```

Each prints a JSON summary indicating both paths, direct estimated cost in CAD, and audited finding types.

## What the demo proves / does not prove

- **Proves:** the deterministic BACAB evaluation software reads structured traces, detects predefined faults and policy-relevant omissions, compares controlled paths, calculates illustrative metrics, stores reviews and exports structured evidence.
- **Does not prove:** real French-language discrimination, real-world population rates, causal language effects, current provider pricing, verified savings/ROI, an automated repair, or a deployed real-banking integration.
- **Caution:** Technical and accessibility stress tests hold language constant, while the language test deliberately injects a difference. These are *designed tests* and not measurements of LLM performance across languages.
- **Cost caveat:** For digital exclusion, a failing path may incur *less* direct tool/LLM cost than a successful one. This is not an economic benefit. Unresolved cases create unmodeled human support/customer costs. BACAB must never optimize cost by denying service.
- **Plan A:** A live LLM subject agent was **not included** in Sprint 1.5; it is now implemented as PLAN A in Sprint 2.6.

See `docs/ARCHITECTURE_SPRINT15.md` and `docs/TEST_REPORT_SPRINT15.md` for the design contract and engineering validation.

---

## Sprint 1.5.1 — Structured dashboard update

**Current release:** `BACAB_WorkstreamB_Sprint1_5_1_Structured_NoBatch.zip`.
Open `START_HERE.txt`, then `docs/SPRINT151_RELEASE_NOTES.md`. The revised dashboard separates internal tool operations from customer-facing prompts, shows baseline/stress costs in hypothetical CAD, corrects specific policy attribution, independently checks terminal outcome claims, and includes human review history in exported audit JSON.

This release intentionally retains a SHARED synthetic testbed with Plan B trace replay; the live LLM-powered subject agent remains upcoming Plan A work. All three agreed flagship recovery cases are preserved. The former Sprint 1.5 package is not overwritten. Python tests passed in the build environment; the user should validate Streamlit rendering on their own Windows PC.

---

## Sprint 2: PLAN A live agent (optional)

See [`START_HERE.txt`](START_HERE.txt) and [`docs/SPRINT2_RELEASE_NOTES.md`](docs/SPRINT2_RELEASE_NOTES.md). Use `requirements-live.txt` to install the optional OpenAI SDK in addition to Streamlit/Pytest. Choose `PLAN A · Live LLM banking agent` in the sidebar, provide your local API key in the masked field, and approve charged usage. The real LLM invokes **fictional local Python tools only**; the shared BACAB auditor remains independent. No real bank or customer data is used. API-reported token usage does not imply real CAD cost; prices are explicitly hypothetical.


## Sprint 2.1 — Sidebar accessibility and controlled Plan A retries

Read `docs/SPRINT21_RELEASE_NOTES.md`. Compared with Sprint 2, the selector and alerts have high-contrast colors, and the `Additional authentication retries` control is enabled in both SHARED and PLAN A for Scenario A. In PLAN A a **deliberately defective Python retry controller** makes 4+N auth attempts after a live model-selected verification request and prevents approved handoff. The extra attempts are **not** model decisions; the trace records `initiated_by=faulty_retry_controller`. If no triggering verification request is made, the dashboard reports that the injected fault did **not** activate. All original modes and fixtures remain available.
