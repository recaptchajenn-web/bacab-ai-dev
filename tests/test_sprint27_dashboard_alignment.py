"""Sprint 2.7: screenshot-matched dashboard presentation, no metric engine changes.

Offline. Does not import Streamlit or invoke the OpenAI API.
"""
from pathlib import Path
import json
import pytest

from bacab_core.presentation import (
    outcome_comparison_card_html, outcome_comparison_labels, duration_display
)
from bacab_core.scenarios import simulate_pair
from bacab_core.evaluators import audit_pair
from bacab_core.replay import load_fixture, import_trace_json

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')


def test_comparison_card_exact_baseline_stress_titles_and_bold_results():
    html = outcome_comparison_card_html('Safe', 'Unresolved')
    assert 'Recovery outcome comparison' in html
    assert '<div class="outcome-compare-side-label">Baseline</div>' in html
    assert '<div class="outcome-compare-side-label">Stress</div>' in html
    assert '<div class="outcome-compare-result">SAFE</div>' in html
    assert '<div class="outcome-compare-result">UNRESOLVED</div>' in html
    assert html.index('>Baseline<') < html.index('>SAFE<')
    assert html.index('>Stress<') < html.index('>UNRESOLVED<')
    assert 'aria-hidden="true">|</div>' in html
    assert '→' not in html


def test_comparison_card_uses_same_card_styling_as_metric():
    assert 'class="outcome-compare-card"' in outcome_comparison_card_html('Safe', 'Unresolved')
    assert '.outcome-compare-card {background:#FFFFFF; border:1px solid #E3E7F1; border-radius:12px;' in APP
    assert 'min-height:98px;' in APP
    assert '.outcome-compare-result {font-size:clamp(' in APP
    assert 'font-weight:800;' in APP
    assert 'grid-template-columns:minmax(0,1fr) auto minmax(0,1.4fr)' in APP
    assert 'st.markdown(outcome_comparison_card_html(baseline_status, stress_status),' in APP
    assert 'st.markdown("**Recovery outcome comparison**")' not in APP


def test_outcome_status_from_metrics_and_no_fixed_safe_unresolved_string():
    for scenario in ('technical_outage', 'digital_exclusion', 'language_disparity', 'control'):
        audit = audit_pair(simulate_pair(scenario))
        base, stress = outcome_comparison_labels(audit['metrics']['baseline'], audit['metrics']['stress'])
        rendered = outcome_comparison_card_html(base, stress)
        assert f'>{base.upper()}<' in rendered
        assert f'>{stress.upper()}<' in rendered
    # Control case must not be falsely shown as degraded.
    assert 'SAFE</div>' in outcome_comparison_card_html('Safe', 'Safe')
    assert 'UNRESOLVED' not in outcome_comparison_card_html('Safe', 'Safe')


def test_comparison_card_escape_untrusted_text():
    html = outcome_comparison_card_html('<script>alert(1)</script>', 'Unresolved & <unsafe>')
    assert '<script>' not in html and '<unsafe>' not in html
    assert '&lt;SCRIPT&gt;' in html and '&amp;' in html
    assert 'role="group"' in html and 'aria-label="Recovery outcome comparison:' in html


@pytest.mark.parametrize('scenario', ['technical_outage', 'digital_exclusion', 'language_disparity', 'control'])
def test_sandbox_and_saved_replay_duration_is_recoded_workflow_with_disclaimer(scenario):
    for audit in (audit_pair(simulate_pair(scenario)), load_fixture(scenario)):
        title, explanation = duration_display(audit)
        assert title == 'Recorded workflow duration'
        assert 'simulated timings' in explanation
        assert 'not actual customer' in explanation


def test_imported_live_trace_retains_recorded_model_tool_title():
    # Synthetic live-style provenance; portable on Windows without user uploads.
    original = audit_pair(simulate_pair('technical_outage'))
    for run in original['runs']:
        run['metadata']['live_model_calls'] = True
        llm_response = next(e for e in run['events'] if e['event_type'] == 'llm_response')
        llm_response['metadata']['usage_source'] = 'api_reported'
    replay = import_trace_json(json.dumps(original))
    assert duration_display(replay)[0] == 'Recorded model/tool duration'
    assert replay['mode'] == 'trace_replay'


def test_customer_burden_number_precedes_description():
    assert "st.write(f\"{diff(s['customer_prompts_requested']-b['customer_prompts_requested'])} difference in customer action requests\")" in APP
    assert 'st.write(f"Difference in customer action requests:' not in APP
    assert 'st.metric("Difference in customer action requests",' in APP


def test_ui_does_not_change_event_schema_metrics_or_hypothetical_pricing():
    audit = audit_pair(simulate_pair('technical_outage'))
    assert audit['schema_version'] == '0.2'
    assert audit['metrics']['baseline']['authentication_attempt_count'] == 2
    assert audit['metrics']['stress']['authentication_attempt_count'] == 4
    assert audit['metrics']['stress']['authentication_over_limit_count'] == 2
    # SHARED scripted LLM decisions carry model-cost shares; live Plan A A had CAD 0.00280.
    # Compare against the *SHARED fixture*, not against a different execution mode.
    fixture = json.loads((ROOT / 'fixtures/technical_outage.json').read_text(encoding='utf-8'))
    assert audit['metrics']['stress']['potentially_avoidable_direct_cost_cad'] == pytest.approx(
        fixture['metrics']['stress']['potentially_avoidable_direct_cost_cad'])


@pytest.mark.parametrize('scenario', ['technical_outage', 'digital_exclusion', 'language_disparity'])
def test_sprint26_bundled_trace_replay_has_identical_evidence_and_cost(scenario):
    # Use shipped fixtures for portable acceptance (not developer-only /mnt/data).
    original = json.loads((ROOT / 'fixtures' / f'{scenario}.json').read_text(encoding='utf-8'))
    audit = load_fixture(scenario)
    assert audit['scenario_id'] == original['scenario_id']
    assert audit['pair_id'] == original['pair_id']
    for variant in ('baseline', 'stress'):
        assert audit['metrics'][variant]['outcome'] == original['metrics'][variant]['outcome']
        assert audit['metrics'][variant]['direct_execution_cost_cad'] == pytest.approx(
            original['metrics'][variant]['direct_execution_cost_cad'])
        assert audit['metrics'][variant]['potentially_avoidable_direct_cost_cad'] == pytest.approx(
            original['metrics'][variant]['potentially_avoidable_direct_cost_cad'])
    assert [e['event_id'] for r in audit['runs'] for e in r['events']] == [
        e['event_id'] for r in original['runs'] for e in r['events']]
