# BACAB Sprint 1.5 — local test evidence

**Execution:** Python environment in the build container, `python -m pytest -q`.

**Result:** 27 automated tests passed. Also checked Python source compilation and CLI responses. This report does not claim a human browser test on the reviewer's Windows PC (still pending).

## Expected functional outputs

| Test | Baseline | Stress | Detector outcome |
|---|---|---|---|
| Control | EN completed | FR completed | No recovery equity alert |
| A · Auth API outage | EN handed off after 2 auth failures | EN unresolved after 4 auth failures | Unbounded retry and missing handoff flagged |
| B · Digital exclusion | EN with accessible phone completed | EN without phone unresolved after 2 unusable offers | Inaccessible/repeated channel and missing handoff flagged |
| C · Language disparity | EN without phone handed off | FR without phone unresolved | Missing equivalent approved fallback flagged |

**Cost:** All displayed charge columns use `cost_cad`, `direct_execution_cost_cad`, and `potentially_avoidable_direct_cost_cad` from hypothetical CAD rates. Tests explicitly verify that failing paths need not be more expensive in direct charges; this must never be used to justify abandoning customers.

**Replay:** Four saved `fixtures/*.json` files reconstruct their audits through the same evaluator. Tests confirm unsupported versions, oversized imports and invalid language/sequence records are rejected. Falsified imported summary metrics are ignored.

**Security:** No batch scripts, PowerShell scripts, executables or API credentials ship in the ZIP. Dependencies are installed through ordinary `pip` from declared requirements.

## Remaining manual acceptance tests

- Scan ZIP and extracted folder with Microsoft Defender.
- Run all four scenarios in the local Streamlit interface; verify outputs and labels.
- Switch to Plan B saved replay and verify a scenario reloads.
- Export CSV and JSON and confirm CAD fields and EN/FR paths.
- Save a human review and confirm it appears in local history.
- Close the app with Ctrl+C and ensure nothing is accessible publicly.
