"""Public Streamlit Community Cloud demo: PLAN A must be unreachable; A/B/C remain available."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from bacab_core.deployment import LOCAL_OPERATOR_ENV, live_agent_enabled
from bacab_core.live_agent import create_openai_client
from bacab_core.scenarios import SCENARIOS

APP = str(Path(__file__).resolve().parents[1] / "app.py")
SCENARIO_IDS = ["technical_outage", "digital_exclusion", "language_disparity"]  # A, B, C


@pytest.fixture(autouse=True)
def public_mode(monkeypatch):
    monkeypatch.delenv(LOCAL_OPERATOR_ENV, raising=False)


def _app():
    return AppTest.from_file(APP, default_timeout=30).run()


def test_live_agent_disabled_by_default():
    assert live_agent_enabled() is False


def test_openai_client_refused_even_with_key_in_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-HIDDEN-TEST-KEY-DO-NOT-USE")
    with pytest.raises(RuntimeError, match="disabled"):
        create_openai_client()


def test_public_sidebar_hides_plan_a_and_api_key_field():
    at = _app()
    assert not at.exception
    options = at.sidebar.radio[0].options
    assert not any(o.startswith("PLAN A") for o in options)
    assert "SHARED · Controlled simulation" in options
    assert "PLAN B · Saved trace replay" in options
    assert not any(t.type == "password" for t in at.sidebar.text_input)


@pytest.mark.parametrize("source", ["SHARED · Controlled simulation", "PLAN B · Saved trace replay"])
@pytest.mark.parametrize("scenario", SCENARIO_IDS)
def test_scenarios_a_b_c_run_in_public_mode(source, scenario):
    at = _app()
    at.sidebar.radio[0].set_value(source).run()
    at.sidebar.selectbox[0].set_value(scenario).run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert any("Audit evaluated" in s.value for s in at.success)
    assert scenario in SCENARIOS


def test_public_sessions_do_not_share_audit_history():
    first = _app()
    first.sidebar.button[0].click().run()
    assert not first.exception
    second = _app()
    assert second.session_state["session_db_path"] != first.session_state["session_db_path"]
    assert any("no saved audits" in c.value for c in second.caption)


def test_local_operator_mode_restores_plan_a(monkeypatch):
    monkeypatch.setenv(LOCAL_OPERATOR_ENV, "1")
    at = _app()
    assert not at.exception
    assert any(o.startswith("PLAN A") for o in at.sidebar.radio[0].options)
