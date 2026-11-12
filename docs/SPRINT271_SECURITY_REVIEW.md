# BACAB AI — Sprint 2.7.1 Security & Reliability Review

**Date:** 2026-11-09  
**Scope:** Frozen Sprint 2.7 hackathon MVP; source review + adversarial local tests.  
**Result:** **Conditional demo release** after four confirmed import/storage/export issues were corrected in the minimal 2.7.1 hotfix. This is **not** certification for production banking, real PII, real customer data, or Internet exposure.

## What was tested

1. Extracted and reviewed actual Sprint 2.7 code (`app.py`, `bacab_core/*`, Streamlit configuration, tests and packaged documentation).
2. Ran Sprint 2.7 regression tests: **129/129 passed before changes**.
3. Executed adversarial tests for history collisions, malformed/non-finite cost JSON, mismatched policy version and CSV spreadsheet formula injection.
4. Added narrowly scoped protections and nine extra offline tests: **138/138 passed**.
5. Imported the three previously recorded actual PLAN A audit JSON files (A, B, C) and compared source event IDs, outcomes and CAD totals to the recomputed PLAN B audits. All matched.
6. Saved an original and a replay with the same canonical pair ID to separate local SQLite records, and checked independent human-review decisions.

## Verified issues and patch decisions

| Issue | Pre-patch observation | Risk | 2.7.1 change | Verification |
|---|---|---|---|---|
| History collision / loss of prior audit | Importing a replay with the same canonical `pair_id` **updated the earlier saved PLAN A record** | **High** for audit integrity | Preserve separate SQLite storage-record keys for distinct evaluations while retaining the original trace pair ID in the JSON | Tested both histories coexist and original stays unchanged |
| Human-review attribution | Reviews were keyed by the canonical pair ID and could follow the overwritten record | **High** for review provenance | Dashboard now uses the returned storage-record ID for `save_review` / `list_reviews` | Tested separate decisions for same source pair |
| Mismatched policy version | A `bank-recovery-v1` trace could be displayed as evaluated against its declared policy while the engine used v2 thresholds | **Medium–High** for misleading audit claim | Reject imported traces unless both runs declare the currently configured policy version | Negative test passes |
| Invalid numerical evidence | Imported non-finite CAD cost (`NaN`, `Infinity`) was accepted, giving unusable `nan` totals | **Medium** for calculation integrity | Strict JSON non-finite parser and finite nonnegative event-cost validation | Negative tests pass |
| Spreadsheet formula injection | Untrusted imported event ID starting with `=...` appeared verbatim in exported CSV | **Medium** when opening untrusted CSV in spreadsheet apps | Escape spreadsheet formula-like text cells in CSV; preserve canonical JSON source unchanged | Malicious import/export regression test passes |

**Pre-existing SQLite history:** The patch prevents **future application-level overwrites**. It cannot restore a live audit that Sprint 2.7 already replaced. Preserve the original downloaded JSON/CSV files as independent evidence. No SQLite migration is needed; the legacy schema remains intact. Distinct evaluations get unique storage keys only when the original pair ID would collide.

## Security controls confirmed in code

- Default Streamlit binding: `127.0.0.1`, `maxUploadSize=3` MB; replay parser limit 2,000,000 characters and 1,000 events per run.
- OpenAI credentials: masked sidebar field or local environment. Application does not put API keys in event payloads, SQLite or JSON/CSV exports. No key is bundled in the release.
- PLAN A: explicit paid-call approval; bounded model/tool-call loops; OpenAI client timeout 30 seconds, SDK automatic retries disabled; use of `store=False` on Responses requests; and a strict whitelist of no-argument fictional banking tools.
- PLAN B: JSON is parsed, not executed. The parser validates the canonical 0.2 structure, pair/variant consistency, terminal-event presence, supported policy version, and outcomes with tool-result evidence; metrics and findings are recomputed from events rather than taken from supplied summary fields.
- Failure handling: a failed live case does not show a stale result as new; model/provider exception bodies are not echoed to the dashboard.
- Human review decisions confirm/reject findings; they do not authorize implementation of fixes.
- Demo's banking environment, customers, pricing and fault injections are fictional.

## Residual limitations (NOT fixed; disclosed)

1. **No authentication of imported event origin.** BACAB can validate and re-evaluate the trace but cannot prove that an external sender generated it honestly, that it is complete, or that its event costs reflect real provider invoices. The dashboard now explicitly states this for user-imported traces. Future work: trusted collection connectors, signed provenance, event hash chains, and evidence retention policies.
2. **No sensitive-data scanner or anonymization on arbitrary uploads.** The demo is for fictional/sanitized traces only. Never import actual bank customer records or real verification codes.
3. **SQLite is local and not tamper-proof or encrypted by BACAB.** The hotfix prevents accidental application-level overwrite of distinct audit evaluations, but a machine user with file access could modify or delete the DB. Use Windows file-system security and keep original exports backed up.
4. **Not a statistical fairness test.** One deliberately injected comparison cannot establish population bias, protected-class discrimination, or legal violations.
5. **No external penetration test, package-vulnerability scan, Windows browser automation, sustained load test, or paid API call was performed during this local review.** The actual Windows visual check and original PLAN A functional runs were previously user-validated.
6. **Fictional CAD costs only.** Replayed event costs are read from the source trace; they are not independently reconciled to API invoices. Historical pricing profile is not authenticated by the import.

## Release recommendation

**Approved for controlled, local, synthetic-data hackathon demo after the Windows smoke test below. Not approved for production or public deployment.** Keep Sprint 2.7 as an immutable backup and use Sprint 2.7.1 for the final demo. Avoid additional core feature development.

## Required Windows smoke test — no API charges

1. Stop older Streamlit processes; extract 2.7.1 into a **new folder**.
2. Install dependencies; run `python -m pytest -q` and expect **138 passed**.
3. Run SHARED Scenario A and confirm the outcomes KPI, policy warnings, and cost panel still render correctly.
4. Run PLAN B → Import JSON with a saved original PLAN A audit, confirm the same outcome and costs, and inspect **Saved History**: the original/replay modes must remain distinct if both were saved in this installation.
5. Optionally save different human-review decisions on the original vs replay and confirm they remain separate.
6. Export JSON and CSV; verify both complete. Do **not** call the paid API for this review.

### Checks not claimed

No real-world security certification, production availability guarantee, protected-group fairness certification, real-cost savings calculation, or automated remediation is established by these tests.
