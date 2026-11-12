"""Sprint 2.6 UX, provenance, safety and historical replay regressions.

Pure offline checks; no Streamlit, OpenAI client or external network needed.
"""
import json
from pathlib import Path
import pytest

from bacab_core.config import load_policy, load_pricing
from bacab_core.evaluators import audit_pair
from bacab_core.presentation import (POLICY_LABELS, policy_display, finding_display,
    outcome_comparison_labels, outcome_comparison_card_html,
    duration_display, equity_notice, pricing_display_rows)
from bacab_core.replay import load_fixture, import_trace_json
from bacab_core.scenarios import simulate_pair


@pytest.mark.parametrize('rule_id', list(load_policy()['policy_rules']))
def test_all_live_policy_identifiers_have_friendly_labels_and_unchanged_ids(rule_id):
    assert rule_id in POLICY_LABELS
    shown = policy_display(rule_id)
    assert shown.startswith(POLICY_LABELS[rule_id])
    assert shown.endswith(f'(`{rule_id}`)')


def test_business_friendly_finding_labels_preserve_trace_source_types():
    assert finding_display('MISSING_APPROVED_FALLBACK') == 'Missing Approved Alternative Recovery'
    assert finding_display('AUTH_RETRY_LIMIT_EXCEEDED') == 'Auth Retry Limit Exceeded'


def make_audit(scenario):
    return audit_pair(simulate_pair(scenario))


@pytest.mark.parametrize('scenario,kind', [
    ('technical_outage','operational'),('digital_exclusion','equity'),
    ('language_disparity','equity'),('control','none')])
def test_concerns_are_proportionate_to_scenario_and_evidence(scenario,kind):
    original_audit = make_audit(scenario)
    notice = equity_notice(original_audit)
    assert notice['kind'] == kind
    assert 'discrimination' not in notice['title'].lower()
    if scenario == 'technical_outage':
        assert 'language or demographic' in notice['description']
        assert 'fairness' not in notice['title'].lower()
    if scenario == 'language_disparity':
        assert 'language-related' in notice['title']
        assert 'intentionally different tool configurations' in notice['description']
    if kind != 'none':
        assert notice['evidence_ids']
        events = {e['event_id'] for run in original_audit['runs'] for e in run['events']}
        assert set(notice['evidence_ids']).issubset(events)
        assert 'not proof' in notice['limitation'].lower()
        assert 'authorization to deploy a fix' in notice['limitation']


def test_outcome_is_comparison_not_same_customer_transition():
    audit = make_audit('technical_outage')
    assert outcome_comparison_labels(audit['metrics']['baseline'],audit['metrics']['stress']) == ('Safe','Unresolved')
    control = make_audit('control')
    assert outcome_comparison_labels(control['metrics']['baseline'],control['metrics']['stress']) == ('Safe','Safe')


@pytest.mark.parametrize('scenario', ['technical_outage','digital_exclusion','language_disparity','control'])
def test_shared_and_bundled_trace_timing_labeled_recorded_workflow_duration(scenario):
    assert duration_display(make_audit(scenario))[0] == 'Recorded workflow duration'
    assert duration_display(load_fixture(scenario))[0] == 'Recorded workflow duration'


def test_imported_live_evidence_still_labeled_recorded_even_in_replay():
    d = make_audit('digital_exclusion')
    assert duration_display(d)[0]=='Recorded workflow duration'
    # Reproduce essential API timing provenance, as recorded in live export metadata.
    for run in d['runs']:
        run['metadata']['live_model_calls']=True
        model_event=next(e for e in run['events'] if e['event_type']=='llm_response')
        model_event['metadata']['usage_source']='api_reported'
    assert duration_display(d)[0]=='Recorded model/tool duration'
    replay=import_trace_json(json.dumps(d))
    assert replay['mode']=='trace_replay'
    assert duration_display(replay)[0]=='Recorded model/tool duration'
    assert 'customer' in duration_display(replay)[1]


def test_mixed_provenance_does_not_hide_unmatched_timing_sources():
    d=make_audit('technical_outage')
    d['runs'][0]['metadata']['live_model_calls']=True
    next(e for e in d['runs'][0]['events'] if e['event_type']=='llm_response')['metadata']['usage_source']='api_reported'
    assert duration_display(d)[0]=='Mixed recorded/simulated duration'


def test_false_metadata_alone_does_not_claim_measured_api_duration():
    d=make_audit('technical_outage')
    for run in d['runs']:
        run['metadata']['live_model_calls']=True
    assert duration_display(d)[0]=='Recorded workflow duration'


def test_pricing_reproduces_exact_configured_rates_and_version():
    prices=load_pricing()
    shown=dict(pricing_display_rows(prices))
    assert shown['Currency']=='CAD'
    assert shown['Input tokens — per 1 million']=='CAD $0.70'
    assert shown['Output tokens — per 1 million']=='CAD $2.80'
    assert shown['One fictional banking-tool execution']=='CAD $0.00140'
    assert shown['Assumptions version']==prices['version']


def test_costs_and_metrics_unchanged_on_fixture_replay():
    metric_keys=('outcome','safe_resolution','customer_prompts_requested',
                 'authentication_attempt_count','authentication_over_limit_count',
                 'direct_execution_cost_cad','potentially_avoidable_direct_cost_cad')
    for scenario in ('technical_outage','digital_exclusion','language_disparity','control'):
        original=json.loads((Path(__file__).resolve().parents[1]/'fixtures'/f'{scenario}.json').read_text(encoding='utf-8'))
        replay=load_fixture(scenario)
        for variant in ('baseline','stress'):
            for key in metric_keys:
                assert replay['metrics'][variant][key]==original['metrics'][variant][key]
        assert [x['finding_type'] for x in replay['findings']]==[x['finding_type'] for x in original['findings']]


def test_app_has_requested_friendly_ui_and_no_raw_json_by_default():
    text=(Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8')
    assert 'outcome_comparison_card_html(baseline_status, stress_status)' in text
    assert 'Difference in customer action requests' in text
    assert 'How costs are calculated' in text
    assert 'Advanced · Inspect/export pricing JSON' in text
    assert 'policy_display(rule_id)' in text
    assert 'duration_display(audit)' in text
    assert 'equity_notice(audit)' in text
    assert 'st.json(pricing)' in text   # advanced only, not default
    assert 'st.json(load_pricing())' not in text
    assert 'Recovery difference' not in text


def test_security_boundaries_in_ui_not_broken():
    app=(Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8')
    assert 'api_key_input = st.text_input' in app and 'type="password"' in app
    assert 'assert_run_matches_selection' in app
    assert 'safe_failure_detail(exc)' in app
    assert 'st.session_state.pop("audit", None)' in app
    assert 'st.session_state["audit_origin"] = "history"' in app
    assert 'live_charge_consent' in app


def test_invalid_replay_rejected_without_executing_content():
    with pytest.raises(ValueError):
        import_trace_json('{}')
    with pytest.raises(ValueError):
        import_trace_json(' '*2_000_001)


def test_no_change_to_auditor_schema_or_prices_and_report_source():
    audit=make_audit('technical_outage')
    assert audit['schema_version']=='0.2'
    assert audit['policy_version']=='bank-recovery-v2'
    assert audit['metrics']['stress']['potentially_avoidable_direct_cost_cad']>0
    assert audit['metrics']['baseline']['potentially_avoidable_direct_cost_cad']==0
