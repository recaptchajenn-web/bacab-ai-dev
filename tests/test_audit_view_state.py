"""Sprint 2.2: tests for scenario identity, stale-result protections and safe errors.

No OpenAI calls, credentials, Streamlit server or network required.
"""
from pathlib import Path
from types import SimpleNamespace
import pytest

from bacab_core.audit_view import selection_key, assert_run_matches_selection, safe_failure_detail, effective_auth_retries
from bacab_core.live_agent import LiveCaseExecutionError, run_live_pair
from bacab_core.scenarios import simulate_pair
from bacab_core.evaluators import audit_pair


def test_selection_switches_invalidate_scenario_identity_and_mode():
    shared_b = selection_key("SHARED · Controlled simulation", "digital_exclusion", 0)
    live_b = selection_key("PLAN A · Live LLM banking agent", "digital_exclusion", 0,
                           model="gpt-6-luna", model_call_limit=8)
    live_c = selection_key("PLAN A · Live LLM banking agent", "language_disparity", 0,
                           model="gpt-6-luna", model_call_limit=8)
    live_a_0 = selection_key("PLAN A · Live LLM banking agent", "technical_outage", 0,
                             model="gpt-6-luna", model_call_limit=8)
    live_a_1 = selection_key("PLAN A · Live LLM banking agent", "technical_outage", 1,
                             model="gpt-6-luna", model_call_limit=8)
    assert len({shared_b, live_b, live_c, live_a_0, live_a_1}) == 5
    assert "secret" not in repr(live_b)


def test_wrong_scenario_c_audit_rejected_when_b_selected():
    report_c = audit_pair(simulate_pair("language_disparity"))
    with pytest.raises(ValueError, match="scenario identity"):
        assert_run_matches_selection(report_c, "PLAN A · Live LLM banking agent", "digital_exclusion")
    with pytest.raises(ValueError, match="must use actual live"):
        assert_run_matches_selection(report_c, "PLAN A · Live LLM banking agent", "language_disparity")
    assert_run_matches_selection(report_c, "SHARED · Controlled simulation", "language_disparity")


def test_stress_report_wrong_source_rejected():
    report_b = audit_pair(simulate_pair("digital_exclusion"))
    with pytest.raises(ValueError, match="actual live"):
        assert_run_matches_selection(report_b, "PLAN A · Live LLM banking agent", "digital_exclusion")
    assert_run_matches_selection(report_b, "PLAN B · Saved trace replay", "digital_exclusion")


def test_safe_diagnostics_never_emit_exception_body_or_key():
    key = "sk-proj-HIDDEN-TEST-KEY-DO-NOT-USE"
    class FakeAPIError(RuntimeError):
        def __init__(self):
            self.status_code = 403
            super().__init__(key)
    report = safe_failure_detail(FakeAPIError())
    assert report == "FakeAPIError, HTTP 403"
    assert key not in report
    wrapped = LiveCaseExecutionError("digital_exclusion", "stress", FakeAPIError())
    assert wrapped.variant == "stress" and wrapped.http_status == 403
    assert key not in str(wrapped)


def test_run_live_pair_reports_baseline_or_stress_failure_without_data_leaks():
    class BrokenResponses:
        def __init__(self, fail_at):
            self.n = 0
            self.fail_at = fail_at
        def create(self, **kwargs):
            self.n += 1
            if self.n == self.fail_at:
                raise RuntimeError("private sensitive response SHOULD NEVER be displayed")
            # A four-step successful baseline before moving to stress.
            steps = ["lookup_account", "request_verification", "verify_one_time_code", "request_recovery"]
            name = steps[(self.n-1) % 4]
            return SimpleNamespace(output=[SimpleNamespace(
                type="function_call", name=name, arguments="{}", call_id=f"c{self.n}")],
                status="completed", usage=SimpleNamespace(input_tokens=100, output_tokens=20))

    for fail_at, expected in [(1, "baseline"), (5, "stress")]:
        responses = BrokenResponses(fail_at)
        with pytest.raises(LiveCaseExecutionError) as e:
            run_live_pair("digital_exclusion", client=SimpleNamespace(responses=responses))
        assert e.value.variant == expected
        assert e.value.scenario_id == "digital_exclusion"
        assert "private sensitive" not in str(e.value)


def test_streamlit_code_clears_old_result_and_shows_provenance():
    # Static guard test does not replace a real browser test.
    app = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'st.session_state.pop("audit", None)' in app
    assert 'st.session_state.get("active_selection") != current_selection' in app
    assert 'assert_run_matches_selection(audit_result, source, scenario)' in app
    assert 'st.session_state["last_run_error"]' in app
    assert 'if not audit:' in app and 'st.stop()' in app
    assert "REPORT IDENTITY" in app


@pytest.mark.parametrize("scenario,selected,expected", [
    ("technical_outage", 0, 0),
    ("technical_outage", 1, 1),
    ("technical_outage", 2, 2),
    ("digital_exclusion", 2, 0),
    ("language_disparity", 1, 0),
    ("control", 2, 0),
])
def test_disabled_scenario_a_slider_value_never_leaks_into_other_scenarios(scenario, selected, expected):
    assert effective_auth_retries(scenario, selected) == expected


def test_invalid_scenario_a_slider_does_not_run():
    with pytest.raises(ValueError, match="retry slider"):
        effective_auth_retries("technical_outage", 4)


def test_app_live_run_uses_effective_retries_and_has_auth_specific_error():
    app = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'effective_retries = effective_auth_retries(scenario, extra_retries)' in app
    assert 'extra_retries=effective_retries))' in app
    assert 'if exc.http_status == 401:' in app
    assert 'paste a current key' in app

