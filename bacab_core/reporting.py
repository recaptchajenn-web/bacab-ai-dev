"""CSV/JSON audit exports, clearly labeled with CAD units."""
import csv
import io
import json


def audit_json(audit: dict) -> bytes:
    return json.dumps(audit, ensure_ascii=False, indent=2).encode("utf-8")


def _safe_spreadsheet_cell(value):
    """Never let untrusted trace identifiers become formulas in Excel/Sheets.

    Canonical JSON retains source evidence verbatim; CSV alone is escaped for
    spreadsheet ingestion. Leading whitespace or a BOM may be ignored by readers.
    """
    if isinstance(value, str) and value.lstrip("\ufeff \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def evidence_csv(audit: dict) -> bytes:
    stream = io.StringIO(newline="")
    columns = ["scenario_id", "run_id", "variant", "language", "sequence", "event_id",
               "actor", "event_type", "tool_name", "tool_call_id", "linked_tool_call_ids", "initiated_by",
               "fault_injected", "policy_rule_ids", "status", "error_code",
               "customer_action_required", "verification_valid_before", "duration_ms",
               "input_tokens", "output_tokens", "cost_cad"]
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for run in audit["runs"]:
        for event in run["events"]:
            row = {**{key: event.get(key) for key in columns},
                             "language": run["cohort_language"],
                             "variant": run["variant"],
                             "initiated_by": event.get("metadata", {}).get("initiated_by", "not_recorded"),
                             "linked_tool_call_ids": ";".join(event.get("metadata", {}).get("linked_tool_call_ids") or []),
                             "fault_injected": event.get("metadata", {}).get("fault_injected", False),
                             "policy_rule_ids": ";".join(event.get("policy_rule_ids") or [])}
            writer.writerow({key: _safe_spreadsheet_cell(value) for key, value in row.items()})
    return stream.getvalue().encode("utf-8-sig")


def audit_json_with_reviews(audit: dict, reviews: list[dict]) -> bytes:
    """Export a reviewed audit without modifying source trace or persisted evaluation.

    'approved' in the legacy SQLite table means the *finding* is confirmed,
    not that code changes, risk exceptions or customer actions were authorized.
    """
    payload = {**audit, "human_reviews": reviews,
               "review_decision_semantics": {
                   "approved": "Finding confirmed; does not approve remediation",
                   "rejected": "Finding rejected by human reviewer",
                   "needs_investigation": "Finding requires investigation",
               }}
    return audit_json(payload)
