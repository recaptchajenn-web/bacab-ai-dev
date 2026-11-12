# PLAN A security and evidence checklist

## Local execution

- Run as ordinary Windows user; Streamlit binds `127.0.0.1` only.
- Scan downloaded archive and extracted files with Windows Defender before setup.
- No `.bat`, `.ps1`, `.exe`, `.dll`, or compiled binaries are included.
- Use a separate Python venv; dependencies are installed from pip and are not bundled as binaries in this ZIP.
- Do not disable Smart App Control or Defender.

## Key handling

- API key can be entered into the masked Streamlit field; it is used for the immediate API client and is not included in BACAB's event metadata, SQLite record, or exports.
- Key may live in Streamlit session memory while the dashboard remains open. Run only locally; do not deploy the interface publicly with that field enabled.
- `OPENAI_API_KEY` can alternatively be supplied through a locally configured Windows environment variable.
- Never share keys in screenshots, transcripts, chat, repositories, or audit exports. Redact any accidental secret in exception logs.

## Execution safety

- The user must explicitly select Plan A, check the paid-usage consent box, and click Run.
- Two journeys are run sequentially; at most 9 model API calls and 12 tool calls *per journey*; actual configured model-call cap defaults to 8.
- Requests use `store=False`, `parallel_tool_calls=False`, no built-in web/computer/code tools, no SDK automatic retries, and a bounded client timeout.
- Banking actions are only hard-coded `MockBank` zero-argument methods, with a strict whitelist and JSON argument validation.
- No production account data, OTP content, customer identifying information, real payments, or banking system connections.

## Evidence and limits

- The model can choose tools; the application does not make claims based on the model's final text. BACAB derives terminal outcomes from verified sandbox tool results.
- Scenario A injects a defective Python retry controller and a missing handoff capability in the stress path; B/C deliberately restrict the approved escalation tool. None is a discovery of natural model bias. Automatic controller retries are recorded with `initiated_by=faulty_retry_controller` and must not be attributed to the LLM.
- The cost tab combines actual API-reported token counts when provided with **fictional CAD unit prices**. It cannot be used to reconcile provider bills or claim savings.
- Stored audit evidence is on the local machine; exporting and sharing files requires normal organizational data controls once real traces are ever added in a future project.

## Acceptance

- `python -m pytest -q`: 50 tests passed in the Sprint 2.1 build environment (including retry-controller and UI styling regression tests).
- Real paid Responses API call: **not executed in the build environment**; requires account/billing and final user-machine validation.
- Streamlit rendering: source compiles; test visually in user's Windows browser as part of Sprint 2 acceptance.
