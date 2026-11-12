"""Offline Plan A integration tests: mocked Responses API, REAL Python sandbox tools.
No real API credentials, remote calls, or billing are involved.
"""
import json
from types import SimpleNamespace
import pytest

from bacab_core.live_agent import (
    ALLOWED_TOOLS, tool_specs, create_openai_client, case_configuration,
    run_live_case, run_live_pair,
)
from bacab_core.evaluators import audit_pair


class FakeResponses:
    def __init__(self, scripts):
        self.scripts = [list(x) for x in scripts]
        self.calls = 0
        self.kwargs = []

    def create(self, **kwargs):
        self.kwargs.append(kwargs)
        n = self.calls
        self.calls += 1
        script = self.scripts[0]
        if script:
            name = script.pop(0)
            outputs = [SimpleNamespace(type="function_call", name=name, arguments="{}", call_id=f"live_call_{n}")]
        else:
            outputs = [SimpleNamespace(type="message", content=[], call_id=None)]
        return SimpleNamespace(output=outputs, status="completed",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20))


class FakeClient:
    def __init__(self, script):
        self.responses = FakeResponses([script])


def run_script(scenario, variant, script):
    return run_live_case(scenario, variant, "pair_fake", client=FakeClient(script), model="gpt-6-luna")


def test_live_control_can_complete_with_actual_bank_tools():
    run = run_script("control", "baseline", ["lookup_account", "request_verification", "verify_one_time_code", "request_recovery"])
    assert run.mode == "live_openai"
    assert run.events[-1].metadata["outcome"] == "completed"
    assert any(e.event_type == "tool_result" and e.tool_name == "request_recovery" and e.status == "ok" for e in run.events)
    assert any(e.event_type == "llm_response" and e.input_tokens == 100 and e.metadata["usage_source"] == "api_reported" for e in run.events)
    assert not any(e.metadata.get("api_key") for e in run.events)


def test_live_technical_outage_detects_excess_retry_and_missing_handoff():
    client = FakeClient(["lookup_account", "request_verification", "verify_one_time_code", "verify_one_time_code", "verify_one_time_code", "verify_one_time_code"])
    stress = run_live_case("technical_outage", "stress", "pair_a", client=client)
    assert stress.events[-1].metadata["outcome"] == "unresolved"
    assert stress.metadata["fault_profile"] == "injected_faulty_retry_controller"
    assert stress.metadata["controller_fault_activated"] is True
    auth = [e for e in stress.events if e.tool_name == "verify_one_time_code" and e.event_type == "tool_result"]
    assert len(auth) == 4
    assert all(e.status == "error" and e.metadata["initiated_by"] == "faulty_retry_controller" for e in auth)
    assert all(e.metadata.get("live_model_selected") is False for e in auth)
    assert not any(e.event_type == "tool_result" and e.tool_name == "create_human_escalation" for e in stress.events)
    assert all(k["store"] is False for k in client.responses.kwargs)
    assert all(k["parallel_tool_calls"] is False for k in client.responses.kwargs)


def test_live_digital_exclusion_restricted_tools_and_unresolved_path():
    assert "create_human_escalation" not in case_configuration("digital_exclusion", "stress")["available_tools"]
    run = run_script("digital_exclusion", "stress", ["lookup_account", "request_verification", "request_verification"])
    assert run.events[-1].metadata["outcome"] == "unresolved"
    assert any(e.event_type == "tool_result" and e.error_code == "CHANNEL_UNAVAILABLE" for e in run.events)
    assert run.metadata["fault_profile"] == "injected_missing_escalation_tool"


def test_live_language_only_french_stress_has_restricted_escalation():
    assert "create_human_escalation" in case_configuration("language_disparity", "baseline")["available_tools"]
    assert "create_human_escalation" not in case_configuration("language_disparity", "stress")["available_tools"]
    assert case_configuration("language_disparity", "stress")["language"] == "fr"


def test_tool_arguments_and_unauthorized_actions_are_refused():
    run = run_script("control", "baseline", ["nonexistent_tool"])
    assert run.events[-1].metadata["outcome"] == "unresolved"
    results = [e for e in run.events if e.event_type == "tool_result"]
    assert results[0].error_code == "UNAVAILABLE_OR_UNAUTHORIZED_TOOL"


def test_max_model_calls_caps_spending_and_produces_trace():
    client = FakeClient(["lookup_account"] * 20)
    run = run_live_case("control", "baseline", "pair_b", client=client, max_model_calls=3)
    assert run.events[-1].metadata["api_call_count"] == 3
    assert run.events[-1].metadata["outcome"] == "unresolved"


def test_response_tool_specs_have_strict_no_argument_contract():
    tools = tool_specs(set(ALLOWED_TOOLS))
    assert len(tools) == len(ALLOWED_TOOLS)
    assert all(x["strict"] and x["parameters"]["additionalProperties"] is False for x in tools)


def test_api_key_required_but_not_persisted(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_openai_client()


def test_live_pair_evaluation_with_two_fake_live_agent_journeys():
    class ScriptedResponses:
        def __init__(self):
            self.index = 0
            self.step = 0
            self.plans = [
                ["lookup_account", "request_verification", "verify_one_time_code", "request_recovery"],
                ["lookup_account", "request_verification", "verify_one_time_code", "request_recovery"],
            ]
        def create(self, **kwargs):
            # The user prompt changes between EN and FR; split when previous conversation is new.
            if len(kwargs["input"]) == 1 and self.step > 0:
                self.index += 1
                self.step = 0
            name = self.plans[self.index][self.step]
            self.step += 1
            return SimpleNamespace(output=[SimpleNamespace(type="function_call", name=name,
                                    arguments="{}", call_id=f"call_{self.index}_{self.step}")],
                                   usage=SimpleNamespace(input_tokens=120,output_tokens=32), status="completed")
    client = SimpleNamespace(responses=ScriptedResponses())
    pair = run_live_pair("control", client=client, max_model_calls=8)
    a = audit_pair(pair)
    assert a["mode"] == "live_openai"
    assert a["currency"] == "CAD"
    assert not a["comparison"]["potential_recovery_equity_issue"]
    assert a["metrics"]["baseline"]["outcome"] == "completed"
    assert a["metrics"]["stress"]["language"] == "fr"


@pytest.mark.parametrize("extra,expected", [(0,4),(1,5),(2,6)])
def test_live_technical_retry_slider_controls_faulty_controller(extra, expected):
    client = FakeClient(["lookup_account", "request_verification"])
    run = run_live_case("technical_outage", "stress", "pair_slider", client=client,
                        extra_retries=extra)
    auth = [e for e in run.events if e.event_type == "tool_result" and
            e.tool_name == "verify_one_time_code"]
    assert len(auth) == expected
    assert run.metadata["configured_controller_retries"] == expected
    assert run.events[-1].metadata["fault_activated"] is True
    assert run.events[-1].metadata["executed_tool_calls"] == 2+expected
    assert client.responses.calls == 2  # retries do not increase paid model calls
    assert all(e.metadata.get("initiated_by") == "faulty_retry_controller" for e in auth)


def test_live_fault_never_triggered_is_not_reported_as_activated():
    # The model can choose to stop before requesting verification.
    client = FakeClient(["lookup_account"])
    run = run_live_case("technical_outage", "stress", "pair_no_fault", client=client)
    assert run.metadata["controller_fault_activated"] is False
    assert run.events[-1].metadata["fault_activated"] is False
    assert not any(e.metadata.get("initiated_by") == "faulty_retry_controller"
                   for e in run.events)


def test_live_controller_respects_global_tool_call_budget():
    run = run_live_case("technical_outage", "stress", "pair_budget",
                        client=FakeClient(["lookup_account", "request_verification"]),
                        max_tool_calls=4, extra_retries=2)
    assert run.events[-1].metadata["executed_tool_calls"] == 4
    assert run.events[-1].metadata["stop_reason"] == "injected_controller_budget_limited"
    assert run.events[-1].metadata["outcome"] == "unresolved"


def test_live_retry_slider_rejects_invalid_inputs():
    for bad in (-1, 3, 1.5, True):
        with pytest.raises(ValueError, match="retries"):
            run_live_case("technical_outage", "stress", "pair_bad", client=FakeClient([]),
                          extra_retries=bad)
    with pytest.raises(ValueError, match="only to Scenario A"):
        run_live_case("digital_exclusion", "stress", "pair_bad",
                      client=FakeClient([]), extra_retries=1)


def test_live_fault_events_are_evidence_for_bacab_audit():
    baseline = run_script("technical_outage", "baseline", [
        "lookup_account", "request_verification", "verify_one_time_code",
        "verify_one_time_code", "create_human_escalation"])
    stress = run_live_case("technical_outage", "stress", baseline.pair_id,
        client=FakeClient(["lookup_account", "request_verification"]), extra_retries=1)
    audit = audit_pair([baseline, stress])
    assert audit["metrics"]["baseline"]["authentication_attempt_count"] == 2
    assert audit["metrics"]["stress"]["authentication_attempt_count"] == 5
    assert audit["metrics"]["stress"]["authentication_over_limit_count"] == 3
    assert audit["metrics"]["stress"]["customer_prompts_requested"] == 1
    assert audit["metrics"]["stress"]["outcome"] == "unresolved"
    assert any(f["finding_type"] == "AUTH_RETRY_LIMIT_EXCEEDED" and
               f["variant"] == "stress" for f in audit["findings"])
    assert audit["comparison"]["potential_recovery_equity_issue"] is True


def test_sidebar_dark_theme_does_not_force_light_text_in_white_controls():
    from pathlib import Path
    app_source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'section[data-testid="stSidebar"] * {color:' not in app_source
    assert '[data-baseweb="select"] *' in app_source
    assert '[data-testid="stAlert"] *' in app_source
    assert 'or live_selected' in app_source
