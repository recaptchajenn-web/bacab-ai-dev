# BACAB AI — Streamlit Community Cloud deployment (hackathon demo)

This repository is the **deployment-safe copy** of the validated Sprint 2.7.1 MVP.

## What judges can use

| Mode | Available publicly |
|---|---|
| SHARED · Controlled simulation — Scenarios A, B, C (+ control) | ✅ |
| PLAN B · Saved (validated) trace replay — bundled `fixtures/*.json` | ✅ |
| PLAN B · Import trace JSON (2 MB cap, validated, never executed) | ✅ |
| PLAN A · Live LLM banking agent | ❌ disabled |

PLAN A is disabled in two places: the option and API-key field are removed from the
sidebar, and `create_openai_client()` refuses to build a client. This holds even if an
`OPENAI_API_KEY` exists in the environment. **Do not add any API key to Streamlit secrets.**

Each browser session writes audits and reviewer notes to its own temporary SQLite file,
so visitors never see each other's history. Nothing persists across app restarts.

## Deploy steps (Streamlit Community Cloud)

1. Sign in at https://share.streamlit.io with the GitHub account that owns this repo.
2. **Create app → Deploy a public app from GitHub**.
3. Repository: `recaptchajenn-web/bacab-ai-dev` · Branch: `main` · Main file path: `app.py`.
4. **Advanced settings → Python version: 3.12.** (Community Cloud sets the Python version
   here, not from a file in the repo.) Leave **Secrets empty**.
5. Deploy. Dependencies install from `requirements.txt` (Streamlit + pandas only;
   the OpenAI SDK is intentionally not included).

## Smoke test after deployment

- Sidebar shows SHARED and two PLAN B options, plus the "PLAN A ... disabled" note; there is no API key field.
- For each of A, B and C, run **SHARED** and **PLAN B · Saved trace replay**; each shows
  "Audit evaluated and stored locally".

## Local operator mode (trusted machine only)

```powershell
python -m pip install -r requirements-live.txt
$env:BACAB_LOCAL_OPERATOR = "1"
python -m streamlit run app.py --server.address 127.0.0.1
```

This brings back PLAN A and the shared `data/bacab.sqlite3` history (git-ignored).
Never set `BACAB_LOCAL_OPERATOR` on a public host.

## Notes

- `SHA256SUMS.txt` lists checksums for the original Sprint 2.7.1 release. `app.py`,
  `bacab_core/live_agent.py`, `.streamlit/config.toml` and `.gitignore` were changed for
  deployment, so their checksums no longer match. That is expected.
- Tests: `python -m pip install -r requirements-dev.txt` then `python -m pytest -q`.
