"""Sprint 2.5 journey visual regressions. All checks are offline."""
from bacab_core.evaluators import audit_pair
from bacab_core.journey_viz import journey_steps, journey_html
from bacab_core.replay import load_fixture
from bacab_core.scenarios import simulate_pair
from bacab_core.live_agent import run_live_case
from test_live_agent import FakeClient


def runs_for(scenario, *, retries=0):
    result = audit_pair(simulate_pair(scenario, extra_retries=retries))
    return {r["variant"]: r for r in result["runs"]}


def auth_steps(steps):
    return [s for s in steps if s["label"].startswith("Attempt ")]


def test_shared_a_baseline_two_attempts_safe_handoff_and_no_third():
    baseline = runs_for("technical_outage")["baseline"]
    steps = journey_steps(baseline)
    assert len(auth_steps(steps)) == 2
    assert all("exceeds" not in s["label"] for s in steps)
    assert any(s["label"] == "Approved human handoff created" for s in steps)
    assert steps[-1]["label"] == "Final outcome — handed off"


def test_shared_a_stress_four_attempts_two_excess_and_unresolved():
    stress = runs_for("technical_outage")["stress"]
    steps = journey_steps(stress)
    assert len(auth_steps(steps)) == 4
    excess = [s for s in steps if "exceeds retry policy" in s["label"]]
    assert len(excess) == 2
    assert [s["label"] for s in excess] == ["Attempt 3 — exceeds retry policy", "Attempt 4 — exceeds retry policy"]
    assert steps[-1]["label"] == "Final outcome — unresolved"
    assert not any("handoff created" in s["label"].lower() for s in steps)


def test_slider_dynamically_increases_attempts_to_six():
    stress = runs_for("technical_outage", retries=2)["stress"]
    steps = journey_steps(stress)
    assert len(auth_steps(steps)) == 6
    assert len([s for s in steps if "exceeds retry policy" in s["label"]]) == 4


def test_digital_exclusion_stress_shows_unusable_channel_not_auth_api_outage():
    runs = runs_for("digital_exclusion")
    baseline = journey_steps(runs["baseline"])
    stress = journey_steps(runs["stress"])
    assert baseline[-1]["label"] == "Final outcome — completed"
    assert stress[-1]["label"] == "Final outcome — unresolved"
    assert sum("unusable channel" in s["label"] for s in stress) == 2
    assert not any("Authentication API unavailable" in s["detail"] for s in stress)


def test_language_disparity_retains_actual_en_fr_differences():
    runs = runs_for("language_disparity")
    assert runs["baseline"]["cohort_language"] == "en"
    assert runs["stress"]["cohort_language"] == "fr"
    assert journey_steps(runs["baseline"])[-1]["label"] == "Final outcome — handed off"
    assert journey_steps(runs["stress"])[-1]["label"] == "Final outcome — unresolved"


def test_control_scenario_is_not_marked_as_auth_outage():
    runs = runs_for("control")
    for variant in ("baseline", "stress"):
        steps = journey_steps(runs[variant])
        assert steps[-1]["label"] == "Final outcome — completed"
        assert not any("API unavailable" in s["label"] for s in steps)


def test_plan_b_fixture_replay_is_supported():
    replay = load_fixture("technical_outage")
    stress = next(r for r in replay["runs"] if r["variant"] == "stress")
    steps = journey_steps(stress)
    assert any("exceeds retry policy" in s["label"] for s in steps)
    assert steps[-1]["label"] == "Final outcome — unresolved"


def test_live_baseline_policy_guard_present_and_stress_controller_provenance():
    baseline = run_live_case("technical_outage", "baseline", "pair_viz",
                             client=FakeClient(["lookup_account", "request_verification",
                                                "verify_one_time_code", "verify_one_time_code"]))
    stress = run_live_case("technical_outage", "stress", "pair_viz",
                           client=FakeClient(["lookup_account", "request_verification"]))
    a = journey_steps(baseline.to_dict())
    b = journey_steps(stress.to_dict())
    assert len(auth_steps(a)) == 2
    assert any("Retry limit enforced" == s["label"] and s["initiated_by"] == "policy_guard" for s in a)
    assert any(s["label"] == "Faulty retry controller started" for s in b)
    assert any(s["initiated_by"] == "faulty_retry_controller" for s in auth_steps(b))
    assert b[-1]["label"] == "Final outcome — unresolved"


def test_html_escapes_untrusted_label_details_and_provenance():
    fake = [{"label": '<img src=x onerror="x">', "detail": "<script>alert('bad')</script>",
             "initiated_by": '<b>agent</b>', "tone": "evil"}]
    html = journey_html(fake, variant="stress", language="en")
    assert "<script>" not in html and "<img" not in html and "<b>agent" not in html
    assert "&lt;script&gt;" in html and "&lt;img" in html and "&lt;b&gt;" in html
    assert 'class="journey-step neutral"' in html


def test_large_import_is_capped_and_preserves_last_outcome():
    stress = runs_for("technical_outage", retries=2)["stress"]
    steps = journey_steps(stress, max_steps=5)
    assert len(steps) == 5
    assert "additional events" in steps[-2]["label"]
    assert steps[-1]["label"] == "Final outcome — unresolved"


def test_reject_invalid_visual_limits():
    import pytest
    with pytest.raises(ValueError):
        journey_steps({"events": []}, max_auth_attempts=0)
    with pytest.raises(ValueError):
        journey_steps({"events": []}, max_steps=2)


def test_app_rendered_immediately_after_journey_comparison_area():
    from pathlib import Path
    app_text = (Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
    assert app_text.index('st.markdown("### Recovery journey · trace-based visual")') > app_text.index('**Journey comparison**')
    assert app_text.index('st.markdown("### Recovery journey · trace-based visual")') < app_text.index('st.markdown("### Assurance lenses")')
    assert 'unsafe_allow_html=True' in app_text
