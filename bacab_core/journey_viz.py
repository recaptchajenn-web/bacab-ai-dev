"""Read-only, trace-derived overview of a matched BACAB audit journey.

The visual is not an additional evaluator. It does not invent actions, reconstruct
hidden model reasoning, or change the canonical trace or audit metrics.
"""
from __future__ import annotations

from html import escape
from typing import Any


def journey_steps(run: dict[str, Any], *, max_auth_attempts: int = 2,
                  max_steps: int = 16) -> list[dict[str, str]]:
    """Display completed tool RESULTS and controller transitions, not requests twice.

    Source evidence is retained on each step; caps prevent a large import from
    dominating the overview while the full trace remains accessible in its tab.
    """
    if max_auth_attempts < 1 or max_steps < 3:
        raise ValueError("Invalid journey visualization limits")
    events = run.get("events") or []
    steps: list[dict[str, str]] = []
    auth_attempts = 0
    failed_auth = 0
    offers = 0
    recovery_attempts = 0

    def add(label: str, tone: str = "neutral", *, detail: str = "",
            event: dict[str, Any] | None = None) -> None:
        source = event or {}
        metadata = source.get("metadata") or {}
        steps.append({
            "label": str(label), "tone": tone, "detail": str(detail),
            "event_id": str(source.get("event_id") or ""),
            "tool_call_id": str(source.get("tool_call_id") or ""),
            "initiated_by": str(metadata.get("initiated_by") or source.get("actor") or ""),
        })

    if any(e.get("event_type") == "customer_message" for e in events):
        msg = next(e for e in events if e.get("event_type") == "customer_message")
        add("Customer request received", event=msg)

    for event in events:
        typ = event.get("event_type")
        metadata = event.get("metadata") or {}
        if typ == "state_transition":
            transition = metadata.get("transition")
            if transition == "retry_limit_reached":
                add("Retry limit enforced", "good", detail="Further authentication calls blocked by policy guard", event=event)
            elif transition == "start_automatic_auth_retries":
                add("Faulty retry controller started", "warning",
                    detail="Subsequent automatic retries are controller-generated, not LLM-selected", event=event)
            elif transition == "controller_stopped_without_handoff":
                add("Controller stopped without handoff", "danger", event=event)
            continue
        if typ != "tool_result":
            continue
        name = event.get("tool_name") or ""
        status = event.get("status")
        error = event.get("error_code") or ""
        if name == "lookup_account":
            add("Account lookup succeeded" if status == "ok" else "Account lookup failed",
                "good" if status == "ok" else "danger", detail=error, event=event)
        elif name == "request_verification":
            offers += 1
            if error == "CHANNEL_UNAVAILABLE":
                add(f"Verification offer {offers} — unusable channel", "danger",
                    detail="Registered device or verification channel unavailable", event=event)
            else:
                add(f"Verification offer {offers}" if status == "ok" else f"Verification offer {offers} failed",
                    "neutral" if status == "ok" else "danger", detail=error, event=event)
        elif name == "verify_one_time_code":
            auth_attempts += 1
            if status == "error":
                failed_auth += 1
            n = event.get("attempt")
            n = n if isinstance(n, int) and n > 0 else auth_attempts
            exceeds = status == "error" and failed_auth > max_auth_attempts
            if exceeds:
                label = f"Attempt {n} — exceeds retry policy"
                tone = "danger"
            elif status == "ok":
                label, tone = f"Attempt {n} — verification succeeded", "good"
            else:
                label, tone = f"Attempt {n} — failed", "warning"
            detail = "Authentication API unavailable" if error == "AUTH_API_UNAVAILABLE" else str(error)
            add(label, tone, detail=detail, event=event)
        elif name == "create_human_escalation":
            usable = (metadata.get("result_flags") or {}).get("usable_handoff") is True
            if status == "ok" and usable:
                add("Approved human handoff created", "good", event=event)
            elif status == "ok":
                add("Handoff returned OK; usability unverified", "warning", event=event)
            else:
                add("Human handoff failed", "danger", detail=error, event=event)
        elif name == "request_recovery":
            recovery_attempts += 1
            valid = event.get("verification_valid_before") is True
            if status == "ok" and valid:
                add("Account recovery completed", "good", event=event)
            elif status == "ok":
                add("Recovery tool succeeded; verification unverified", "warning", event=event)
            else:
                add(f"Recovery attempt {recovery_attempts} failed", "danger", detail=error, event=event)
        else:
            add(f"Tool {name or 'unknown'} — {'succeeded' if status == 'ok' else 'failed'}",
                "good" if status == "ok" else "danger", detail=error, event=event)

    outcome_events = [e for e in events if e.get("event_type") == "outcome"]
    if outcome_events:
        outcome_event = outcome_events[-1]
        outcome = (outcome_event.get("metadata") or {}).get("outcome")
        if outcome == "completed":
            add("Final outcome — completed", "good", event=outcome_event)
        elif outcome == "handed_off":
            add("Final outcome — handed off", "good", detail="Safe recovery path; account restoration not confirmed", event=outcome_event)
        elif outcome == "unresolved":
            add("Final outcome — unresolved", "danger", event=outcome_event)
        else:
            add("Final outcome — not recorded", "warning", event=outcome_event)

    if len(steps) > max_steps:
        omitted = len(steps) - (max_steps - 1)
        return steps[:max_steps - 2] + [{
            "label": f"{omitted} additional events — see Execution traces", "tone": "neutral",
            "detail": "", "event_id": "", "tool_call_id": "", "initiated_by": "",
        }] + [steps[-1]]
    return steps


def journey_html(steps: list[dict[str, str]], *, variant: str, language: str) -> str:
    """Safe HTML fragment for Streamlit, escaping all values from imported traces."""
    title = "BASELINE" if variant == "baseline" else "STRESS"
    lang = {"en": "English", "fr": "French"}.get(language, "Language not recorded")
    parts = [f'<div class="journey-panel"><div class="journey-label">{title} <span>· {escape(lang)}</span></div>',
             '<div class="journey-flow">']
    for item in steps:
        tone = item.get("tone", "neutral")
        tone = tone if tone in {"neutral", "good", "warning", "danger"} else "neutral"
        label = escape(item.get("label", ""), quote=True)
        detail = escape(item.get("detail", ""), quote=True)
        source = escape(item.get("initiated_by", ""), quote=True)
        detail_html = f'<div class="journey-detail">{detail}</div>' if detail else ""
        source_html = f'<div class="journey-origin">Origin: {source}</div>' if source and source not in {"customer", "system"} else ""
        parts.append(f'<div class="journey-step {tone}"><div class="journey-step-title">{label}</div>'
                     + detail_html + source_html + '</div>')
    parts += ['</div></div>']
    return "".join(parts)
