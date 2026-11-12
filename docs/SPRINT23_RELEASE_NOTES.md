# Sprint 2.3 — API authentication triage and B/C scenario selection fix

## What is fixed
- Disabled Scenario A retry slider state can no longer leak into B, C, or Control.
- HTTP 401 now produces specific on-screen credential triage guidance rather than a generic scenario failure.
- The app still refuses to display or store incomplete audits.

## What software cannot fix
- HTTP 401 is a provider authentication response. A revoked, expired, or wrong project key must be replaced in the local masked key field by the operator.
- Do not disable Windows security controls or grant unrestricted API scopes. Restricted Responses permission is sufficient for this app.

## Validation
- Run: `./.venv/Scripts/python.exe -m pytest -q` on Windows PowerShell.
- No network or paid API calls are required for this regression suite.
- First run SHARED B and C, and switch from A slider value 1 to C to verify no validation error.
- Only after checking the key run ONE PLAN A control test, then scenario B.
- Preserve existing older project folders as working backups.
