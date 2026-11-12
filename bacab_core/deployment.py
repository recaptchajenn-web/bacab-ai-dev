"""Deployment mode for the public hackathon demo.

PUBLIC DEMO (default, used on Streamlit Community Cloud):
  * PLAN A live LLM execution is disabled; no API key field is shown and no
    OpenAI client can be created.
  * Each browser session gets its own temporary SQLite file, so judges never
    see each other's audits, imported traces or reviewer notes.

LOCAL OPERATOR mode is opt-in only, on a trusted machine:
    $env:BACAB_LOCAL_OPERATOR = "1"     # PowerShell
  It restores the original Sprint 2.7.1 behaviour (PLAN A + shared local
  data/bacab.sqlite3 history). Never set this variable on a public host.
"""
from __future__ import annotations

import os

LOCAL_OPERATOR_ENV = "BACAB_LOCAL_OPERATOR"


def local_operator_mode() -> bool:
    return os.getenv(LOCAL_OPERATOR_ENV, "").strip() == "1"


def live_agent_enabled() -> bool:
    """PLAN A live API execution is available only in explicit local operator mode."""
    return local_operator_mode()
