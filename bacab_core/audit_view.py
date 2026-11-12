"""Pure, testable view-state rules preventing stale audits from appearing as fresh runs.

No Streamlit dependency. Authentication credentials must NEVER enter these values.
"""
from __future__ import annotations
from typing import Any


def effective_auth_retries(scenario: str, slider_value: int) -> int:
    """Only technical-outage scenario uses the A retry slider.

    Streamlit may retain the slider's last value after disabling it.
    Normalize at the execution boundary rather than trusting widget state.
    """
    if scenario != "technical_outage":
        return 0
    if type(slider_value) is not int or slider_value not in (0, 1, 2):
        raise ValueError("Scenario A retry slider must be between 0 and 2")
    return slider_value


def selection_key(source: str, scenario: str, extra_retries: int, *,
                  model: str = "", model_call_limit: int = 0) -> tuple:
    """The complete non-secret selection whose change invalidates an active audit."""
    if source.startswith("PLAN A"):
        return source, scenario, extra_retries, model, model_call_limit
    if source.startswith("SHARED"):
        return source, scenario, extra_retries
    return source, scenario


def assert_run_matches_selection(audit: dict[str, Any], source: str, scenario: str) -> None:
    """Reject a mismatched report BEFORE storing or displaying it as this run."""
    actual_scenario = audit.get("scenario_id")
    if source.startswith("PLAN B") and "Import" in source:
        # Uploaded trace carries its own explicit scenario identity.
        return
    if actual_scenario != scenario:
        raise ValueError("Audit scenario identity does not match the selected scenario")
    actual_mode = audit.get("mode")
    if source.startswith("PLAN A") and actual_mode != "live_openai":
        raise ValueError("PLAN A must use actual live agent traces, not synthetic/replayed evidence")
    if source.startswith("SHARED") and actual_mode != "sandbox_synthetic":
        raise ValueError("SHARED mode must use controlled synthetic traces")


def safe_failure_detail(exc: BaseException) -> str:
    """Produce safe, bounded diagnostic metadata; never include exception body or key."""
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if type(status) is int and 100 <= status <= 599:
        return f"{name}, HTTP {status}"
    return name
