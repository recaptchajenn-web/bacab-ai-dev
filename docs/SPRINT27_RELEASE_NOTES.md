# BACAB AI — Sprint 2.7: KPI presentation refinements

**Release date:** 2026-11-09. **Scope:** three presentation-only changes requested after Sprint 2.6 Windows visual review.

## What changed

1. **Recovery outcome comparison** is now rendered as a real KPI-style card, matching the adjacent baseline and stress cards: white background, 1 px gray border, rounded corners, same minimum card height, small heading, then two columns labeled **Baseline** and **Stress** above large bold outcome words. Example: **SAFE | UNRESOLVED**. No arrow that could suggest chronological progression. Labels are derived from the current audit, not hard-coded to Scenario A. A no-fault control can show **SAFE | SAFE**. HTML content is escaped and an accessible descriptive label is provided.
2. **Duration KPI:** For SHARED and bundled simulated PLAN B traces, use **Recorded workflow duration**, matching the agreed screenshot. The explanatory caption explicitly states that values are recorded *synthetic/fixture timings*, **not** customer waiting or actual banking-system latency. When PLAN B imports a genuine live PLAN A trace, the KPI continues to say **Recorded model/tool duration** because that source includes model API timings; model and fictional local-tool timing remain distinct. Mixed provenance is still identified separately. All duration arithmetic remains unchanged.
3. In **Customer recovery burden**, the first line is now **+0 difference in customer action requests** (or the computed signed count), so the signed number precedes the description like its neighboring lines. The main KPI retains a short descriptive label and a large signed number.

## Preserved behavior

- All three evidence modes: SHARED deterministic simulator, PLAN A live OpenAI LLM + fictional banking tools, PLAN B saved/imported traces.
- No changes to audit metrics, event trace schema v0.2, bank tool results, error handling, hypothetical CAD rates, fairness-risk rules, human review, or exports.
- All six Sprint 2.6 approved UX improvements remain present, including scenario-appropriate fairness concern, friendly policy title with technical rule ID, and readable pricing assumptions.
- In Scenario A, the deliberately broken retry controller is still correctly identified as the source of excess calls. This is **not evidence of demographic bias**.

## Verification

- **129 offline automated tests pass** in this build (115 prior + 14 additional). Included 4 scenario-specific timing checks, KPI HTML escaping and responsive-style checks, signed-number ordering, preservation of simulator audit metrics, and reproducible shipped trace replay.
- Independently imported all three previously validated **user-supplied actual PLAN A JSON audits** (Scenario A, B, C). Their pair IDs, trace event IDs, outcomes and audited cost values match the original export; `Recorded model/tool duration` still shown for imported live evidence.
- Tested package files for Python syntax and ZIP integrity; computed SHA-256 checksums for source files.
- **Not verified here:** real Streamlit browser rendering on the user's Windows machine (Streamlit is not installed in this isolated packaging environment); no paid API calls or public deployment.

## Local checks

1. Unzip into a **new directory**; do not overwrite working Sprint 2.6 or saved SQLite history. Run `python -m pytest -q` using the project's `.venv` and confirm **129 passed**.
2. SHARED → Scenario A → Run. In **Recovery outcomes**, confirm three matching white KPI cards; the third contains `Recovery outcome comparison`, then small `Baseline` above bold `SAFE` and small `Stress` above bold `UNRESOLVED`, with a central vertical bar.
3. On **Key differences**, ensure **Recorded workflow duration** replaces **Simulated duration** for this SHARED run; the caption clarifies that synthetic timings are not customer waiting.
4. In **Customer recovery burden**, confirm the line reads **+0 difference in customer action requests**.
5. Optional no-cost check: PLAN B → Import trace JSON → import existing PLAN A audit JSON; duration should say **Recorded model/tool duration**, since its evidence came from the live agent. No API key or paid calls required.
6. Check B/C/Control for dynamic outcome labels; do not make any new paid live PLAN A calls for this UI-only change.

See `START_SPRINT27_WINDOWS.txt` for PowerShell setup.
