"""Business-readable explanations derived from existing BACAB audit evidence.

Presentation-only: never modifies original policy IDs, findings, metrics, traces,
pricing assumptions or review decisions. Kept pure for offline regression tests.
"""
from __future__ import annotations
from typing import Any
from html import escape

POLICY_LABELS = {
    "VERIFY_BEFORE_RECOVERY": "Verification Required Before Account Recovery",
    "VERIFY_ONCE_WHILE_VALID": "Do Not Repeat Valid Verification",
    "AUTH_OUTAGE_BOUNDED_RETRIES": "Authentication Retry Limit",
    "ACCESSIBLE_FALLBACK_REQUIRED": "Usable Alternative Recovery Required",
    "EQUIVALENT_APPROVED_FALLBACK": "Equal Access to Approved Recovery Assistance",
    "ESCALATE_AFTER_FAILURES": "Human Assistance Required After Repeated Failures",
    "NO_REAL_BANK_ACCESS": "Simulation Only — No Real Banking Access",
}

FINDING_LABELS = {
    "MISSING_APPROVED_FALLBACK": "Missing Approved Alternative Recovery",
    "REPEATED_UNUSABLE_FALLBACK": "Repeated Unusable Recovery Option",
}


def policy_display(rule_id: str) -> str:
    """Friendly label plus UNCHANGED machine-readable identifier."""
    return f"{POLICY_LABELS.get(rule_id, rule_id.replace('_', ' ').title())} (`{rule_id}`)"


def finding_display(finding_type: str) -> str:
    return FINDING_LABELS.get(finding_type, finding_type.replace("_", " ").title())


def outcome_comparison_labels(baseline: dict, stress: dict) -> tuple[str, str]:
    """Labels for separate journeys, never a chronological transition."""
    def label(metrics: dict) -> str:
        if metrics["safe_resolution"]:
            return "Safe"
        if metrics["outcome"] == "unresolved":
            return "Unresolved"
        return "Review required"
    return label(baseline), label(stress)


def outcome_comparison_card_html(baseline_status: str, stress_status: str) -> str:
    """Render an accessible comparison in a KPI-sized card, never a journey arrow.

    Escaping keeps even unexpected imported status labels safe to display.
    """
    baseline = escape(str(baseline_status).upper(), quote=True)
    stress = escape(str(stress_status).upper(), quote=True)
    aria = escape(f"Recovery outcome comparison: Baseline {baseline_status}; Stress {stress_status}", quote=True)
    return (
        f'<div class="outcome-compare-card" role="group" aria-label="{aria}">'
        '<div class="outcome-compare-title">Recovery outcome comparison</div>'
        '<div class="outcome-compare-values">'
        '<div class="outcome-compare-side">'
        '<div class="outcome-compare-side-label">Baseline</div>'
        f'<div class="outcome-compare-result">{baseline}</div></div>'
        '<div class="outcome-compare-divider" aria-hidden="true">|</div>'
        '<div class="outcome-compare-side">'
        '<div class="outcome-compare-side-label">Stress</div>'
        f'<div class="outcome-compare-result">{stress}</div></div>'
        '</div></div>'
    )


def _api_timed(run: dict) -> bool:
    """Infer source from original trace provenance, not the replay's new mode."""
    return bool(run.get("metadata", {}).get("live_model_calls") is True and
                any(event.get("event_type") == "llm_response" and
                    event.get("metadata", {}).get("usage_source") == "api_reported"
                    for event in run.get("events", [])))


def duration_display(audit: dict) -> tuple[str, str]:
    runs = audit.get("runs", [])
    flags = [_api_timed(run) for run in runs]
    if flags and all(flags):
        return ("Recorded model/tool duration",
                "Includes measured model API-call time and local fictional banking-tool timings. "
                "It does not measure the customer's total waiting or recovery time.")
    if any(flags):
        return ("Mixed recorded/simulated duration",
                "Journeys contain different timing sources. Compare with caution; "
                "this is not the customer's total waiting time.")
    return ("Recorded workflow duration",
            "Recorded from deterministic sandbox/fixture events; simulated timings, not actual "
            "customer waiting or real banking-system latency.")


def equity_notice(audit: dict) -> dict[str, Any]:
    """Conservative, scenario-specific triage cue; never claim bias or illegality.

    A differential recovery flag alone is not evidence of demographic bias.
    Identifiers refer to existing deterministic findings and trace events.
    """
    scenario = audit.get("scenario_id")
    cmp = audit.get("comparison", {})
    b = audit.get("metrics", {}).get("baseline", {})
    s = audit.get("metrics", {}).get("stress", {})
    flagged = bool(cmp.get("potential_recovery_equity_issue"))
    supported = bool(b.get("safe_resolution") and not s.get("safe_resolution"))
    findings = [f for f in audit.get("findings", []) if f.get("variant") == "stress"]
    serious = [f for f in findings if f.get("finding_type") in {
        "DIFFERENTIAL_RECOVERY_BURDEN", "MISSING_APPROVED_FALLBACK", "AUTH_RETRY_LIMIT_EXCEEDED"}]
    evidence = list(dict.fromkeys(event_id for finding in serious
                                  for event_id in finding.get("observed_evidence_ids", [])))
    if not flagged:
        return {"kind": "none", "title": "No differential recovery concern flagged in this controlled pair",
                "description": "A single test is not evidence that all customer journeys are equitable.",
                "evidence_ids": []}
    if scenario == "technical_outage":
        title = "Operational resilience concern — human investigation recommended"
        explanation = ("The stress workflow exceeded the permitted authentication attempts or failed "
                       "to provide a usable handoff. This compares retry-controller behavior, "
                       "not language or demographic groups.")
        kind = "operational"
    elif scenario == "digital_exclusion":
        title = "Potential recovery accessibility/equity concern — human investigation recommended"
        explanation = ("A customer without the registered phone lacked a usable alternative recovery path. "
                       "Investigate channel accessibility and approved assistance.")
        kind = "equity"
    elif scenario == "language_disparity":
        title = "Potential language-related recovery equity concern — human investigation recommended"
        explanation = ("With the same unavailable-phone condition, English and French paths had "
                       "different access to a human handoff because of intentionally different tool configurations.")
        kind = "equity"
    else:
        title = "Potential recovery-path difference — human investigation recommended"
        explanation = "The controlled journeys differ. Investigate the actual evidence and relevant policy."
        kind = "review"
    if supported:
        explanation += " Baseline had a safe path; stress was unresolved."
    return {"kind": kind, "title": title, "description": explanation,
            "evidence_ids": evidence[:8],
            "limitation": ("Controlled, deliberately injected single-pair comparison. Not proof of inherent "
                           "model bias, population-level discrimination, causal effects or legal noncompliance. "
                           "Human review confirms a finding, not authorization to deploy a fix.")}


def pricing_display_rows(pricing: dict) -> list[tuple[str, str]]:
    return [
        ("Currency", str(pricing["currency"])),
        ("Input tokens — per 1 million", f'CAD ${pricing["input_cad_per_1m_tokens"]:,.2f}'),
        ("Output tokens — per 1 million", f'CAD ${pricing["output_cad_per_1m_tokens"]:,.2f}'),
        ("One fictional banking-tool execution", f'CAD ${pricing["tool_call_cad"]:,.5f}'),
        ("Illustrative pricing profile", str(pricing["model"])),
        ("Assumptions version", str(pricing["version"])),
    ]
