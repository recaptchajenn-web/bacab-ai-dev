"""Sprint 2.4 regression tests. Fake Responses objects; never bill an OpenAI API."""
from dataclasses import replace
import csv
import io

import pytest

from bacab_core.evaluators import audit_pair, evaluate_run
from bacab_core.live_agent import run_live_case
from bacab_core.reporting import evidence_csv, audit_json
from bacab_core.scenarios import simulate_pair
from bacab_core.schema import new_id
from test_live_agent import FakeClient


def live_a(variant, script, *, max_tool_calls=12, extra_retries=0):
    return run_live_case("technical_outage", variant, "pair_sprint24",
                         client=FakeClient(script), max_tool_calls=max_tool_calls,
                         extra_retries=extra_retries)


def by_tool(run, name):
    return [e for e in run.events if e.event_type == "tool_result" and e.tool_name == name]


def test_live_baseline_guard_stops_at_two_even_if_model_script_requests_six():
    run = live_a("baseline", ["lookup_account", "request_verification"] + ["verify_one_time_code"]*6)
    assert len(by_tool(run, "verify_one_time_code")) == 2
    assert run.events[-1].metadata["outcome"] == "handed_off"
    assert run.events[-1].metadata["stop_reason"] == "baseline_policy_guard_safe_handoff"
    assert evaluate_run(run)["authentication_over_limit_count"] == 0
    handoff = by_tool(run, "create_human_escalation")
    assert len(handoff) == 1
    assert handoff[0].metadata["initiated_by"] == "policy_guard"
    assert not handoff[0].metadata["live_model_selected"]
    assert sum(e.event_type == "llm_response" for e in run.events) == 4


def test_policy_guard_handoff_has_separate_call_id_and_policy_reference():
    run = live_a("baseline", ["lookup_account", "request_verification", "verify_one_time_code", "verify_one_time_code"])
    handoff = by_tool(run, "create_human_escalation")[0]
    call = next(e for e in run.events if e.event_type == "tool_call" and e.tool_call_id == handoff.tool_call_id)
    assert call.metadata["initiated_by"] == "policy_guard"
    assert call.tool_call_id == handoff.tool_call_id
    assert "AUTH_OUTAGE_BOUNDED_RETRIES" in handoff.policy_rule_ids
    assert any(e.event_type == "state_transition" and e.metadata.get("blocked_future_calls") for e in run.events)


def test_baseline_can_escalate_early_without_guard():
    run = live_a("baseline", ["lookup_account", "request_verification", "verify_one_time_code", "create_human_escalation"])
    assert len(by_tool(run, "verify_one_time_code")) == 1
    assert by_tool(run, "create_human_escalation")[0].metadata["initiated_by"] == "llm"
    assert run.events[-1].metadata["outcome"] == "handed_off"


def test_policy_guard_does_not_exceed_global_tool_budget_to_handoff():
    run = live_a("baseline", ["lookup_account", "request_verification"] + ["verify_one_time_code"]*6,
                 max_tool_calls=4)
    assert len(by_tool(run, "verify_one_time_code")) == 2
    assert by_tool(run, "create_human_escalation") == []
    assert run.events[-1].metadata["outcome"] == "unresolved"
    assert run.events[-1].metadata["stop_reason"] == "baseline_policy_guard_tool_budget_exhausted"
    assert run.events[-1].metadata["executed_tool_calls"] == 4


def test_live_stress_retries_remain_faulty_controller_generated_with_slider():
    run = live_a("stress", ["lookup_account", "request_verification"], extra_retries=2)
    attempts = by_tool(run, "verify_one_time_code")
    assert len(attempts) == 6
    assert {e.metadata["initiated_by"] for e in attempts} == {"faulty_retry_controller"}
    assert run.events[-1].metadata["outcome"] == "unresolved"
    assert evaluate_run(run)["authentication_over_limit_count"] == 4


def test_live_baseline_and_stress_share_same_auditor_with_clean_control():
    baseline = live_a("baseline", ["lookup_account", "request_verification", "verify_one_time_code", "verify_one_time_code"])
    stress = live_a("stress", ["lookup_account", "request_verification"], extra_retries=1)
    # Both case runs need same parent pair; helper supplies it.
    result = audit_pair([baseline, stress])
    assert result["metrics"]["baseline"]["authentication_over_limit_count"] == 0
    assert result["metrics"]["stress"]["authentication_over_limit_count"] == 3
    assert result["metrics"]["baseline"]["potentially_avoidable_direct_cost_cad"] == 0
    assert result["comparison"]["potential_recovery_equity_issue"]


def test_live_unnecessary_controller_attempts_are_tool_only_cost():
    run = live_a("stress", ["lookup_account", "request_verification"])
    metrics = evaluate_run(run)
    rows = metrics["flagged_unnecessary_operations_cost_breakdown"]
    assert len(rows) == 2
    assert all(r["component"] == "tool_result" for r in rows)
    assert all(r["initiated_by"] == "faulty_retry_controller" for r in rows)
    assert metrics["potentially_avoidable_direct_cost_cad"] == pytest.approx(.0028)


def test_synthetic_unnecessary_cost_uses_explicit_model_and_tool_link():
    pair = simulate_pair("technical_outage")
    stress = pair[1]
    metrics = evaluate_run(stress)
    flagged = metrics["flagged_unnecessary_operations_cost_breakdown"]
    assert len(flagged) == 4  # two model shares plus two tool results
    assert {r["component"] for r in flagged} == {"tool_result", "llm_response_share"}
    assert all(r["tool_call_id"] for r in flagged)
    assert metrics["potentially_avoidable_direct_cost_cad"] == pytest.approx(.0031668)


def test_unrelated_adjacent_model_event_not_assigned_to_controller_retry():
    run = live_a("stress", ["lookup_account", "request_verification"])
    cost_before = evaluate_run(run)["potentially_avoidable_direct_cost_cad"]
    idx = next(i for i,e in enumerate(run.events) if e.event_type == "tool_result" and
               e.tool_name == "verify_one_time_code" and e.attempt == 3)
    unrelated = replace(run.events[1], event_id=new_id("evt"), sequence=-1,
                        event_type="llm_response", tool_name=None, tool_call_id=None,
                        cost_cad=5.0, metadata={"initiated_by": "llm", "linked_tool_call_ids": []})
    run.events.insert(idx, unrelated)
    for i, e in enumerate(run.events, 1):
        e.sequence = i
    run.validate()
    assert evaluate_run(run)["potentially_avoidable_direct_cost_cad"] == cost_before


def test_csv_exposes_provenance_call_id_and_policy():
    result = audit_pair(simulate_pair("technical_outage"))
    header = next(csv.DictReader(io.StringIO(evidence_csv(result).decode("utf-8-sig"))))
    assert {"initiated_by", "tool_call_id", "linked_tool_call_ids", "policy_rule_ids", "fault_injected"} <= set(header)
    reader = csv.DictReader(io.StringIO(evidence_csv(result).decode("utf-8-sig")))
    rows = list(reader)
    excess = [r for r in rows if r["variant"] == "stress" and r["event_type"] == "tool_result" and
              r["tool_name"] == "verify_one_time_code"][-1]
    assert excess["initiated_by"] == "scripted_simulation"
    assert excess["tool_call_id"].startswith("call_")
    assert "AUTH_OUTAGE_BOUNDED_RETRIES" in excess["policy_rule_ids"]


def test_b_c_and_control_synthetic_regression():
    for scenario in ("control", "digital_exclusion", "language_disparity"):
        audit = audit_pair(simulate_pair(scenario))
        assert audit["scenario_id"] == scenario
        assert all("flagged_unnecessary_operations_cost_breakdown" in m for m in audit["metrics"].values())


def test_old_trace_without_link_excludes_unrelated_model_cost():
    run = simulate_pair("technical_outage")[1]
    for event in run.events:
        if event.event_type == "llm_response":
            event.metadata.pop("linked_tool_call_ids", None)
            event.tool_call_id = None
    result = evaluate_run(run)
    assert result["potentially_avoidable_direct_cost_cad"] == pytest.approx(.0028)


def test_audit_json_contains_cost_breakdown():
    pair = simulate_pair("technical_outage")
    result = audit_pair(pair)
    assert b'flagged_unnecessary_operations_cost_breakdown' in audit_json(result)
