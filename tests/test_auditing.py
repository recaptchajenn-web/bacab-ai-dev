"""Sprint 1.5 acceptance checks: three flagship stress tests, CAD and Plan B."""
from __future__ import annotations
import csv
import io
import json
from pathlib import Path
import pytest
from bacab_core.schema import Run
from bacab_core.scenarios import SCENARIOS, simulate_pair
from bacab_core.evaluators import audit_pair
from bacab_core.replay import import_trace_json, load_fixture
from bacab_core.storage import save_audit, load_audit, list_audits, save_review, list_reviews
from bacab_core.config import load_pricing, load_policy
from bacab_core.reporting import audit_json, evidence_csv, audit_json_with_reviews


def make(name="digital_exclusion", retries=0):
    return audit_pair(simulate_pair(name, extra_retries=retries))


def finding_types(audit, variant=None):
    return {f["finding_type"] for f in audit["findings"] if variant is None or f["variant"] == variant}


def test_control_en_fr_both_recover_without_equity_issue():
    audit = make("control")
    b, s = audit["metrics"]["baseline"], audit["metrics"]["stress"]
    assert (b["language"], s["language"]) == ("en", "fr")
    assert b["outcome"] == s["outcome"] == "completed"
    assert b["safe_resolution"] and s["safe_resolution"]
    assert b["customer_actions"] == s["customer_actions"] == 1
    assert not audit["comparison"]["potential_recovery_equity_issue"]
    assert audit["findings"] == []


def test_technical_outage_both_english_same_api_condition():
    audit = make("technical_outage")
    base, stress = audit["runs"]
    assert (base["cohort_language"], stress["cohort_language"]) == ("en", "en")
    assert base["metadata"]["auth_api_available"] is False
    assert stress["metadata"]["auth_api_available"] is False
    assert audit["metrics"]["baseline"]["authentication_attempt_count"] == 2
    assert audit["metrics"]["stress"]["authentication_attempt_count"] == 4
    assert audit["metrics"]["baseline"]["outcome"] == "handed_off"
    assert audit["metrics"]["stress"]["outcome"] == "unresolved"
    assert audit["metrics"]["baseline"]["usable_handoff"]
    assert not audit["metrics"]["stress"]["usable_handoff"]


def test_technical_outage_flags_loop_missing_escalation():
    audit = make("technical_outage")
    assert audit["metrics"]["stress"]["loop_count"] >= 2
    assert {"AUTH_RETRY_LIMIT_EXCEEDED", "MISSING_APPROVED_FALLBACK"} <= finding_types(audit, "stress")
    assert audit["comparison"]["potential_recovery_equity_issue"]


def test_technical_additional_retries_are_measureable():
    base = make("technical_outage", 0)["metrics"]["stress"]
    plus = make("technical_outage", 2)["metrics"]["stress"]
    assert plus["authentication_attempt_count"] == base["authentication_attempt_count"] + 2
    assert plus["loop_count"] == base["loop_count"] + 2
    assert plus["direct_execution_cost_cad"] > base["direct_execution_cost_cad"]


def test_digital_exclusion_both_english_but_device_access_differs():
    audit = make("digital_exclusion")
    b, s = audit["runs"]
    assert b["cohort_language"] == s["cohort_language"] == "en"
    assert b["metadata"]["device_accessible"] is True
    assert s["metadata"]["device_accessible"] is False
    assert audit["metrics"]["baseline"]["outcome"] == "completed"
    assert audit["metrics"]["stress"]["outcome"] == "unresolved"


def test_digital_exclusion_missing_approved_channel_flagged():
    audit = make("digital_exclusion")
    m = audit["metrics"]["stress"]
    assert m["unusable_channel_offers"] == 2
    assert m["customer_actions"] == 2
    assert m["loop_count"] >= 1
    assert {"INACCESSIBLE_CHANNEL", "REPEATED_UNUSABLE_FALLBACK", "MISSING_APPROVED_FALLBACK"} <= finding_types(audit, "stress")


def test_language_disparity_is_en_fr_with_both_phones_unavailable():
    audit = make("language_disparity")
    b, s = audit["runs"]
    assert (b["cohort_language"], s["cohort_language"]) == ("en", "fr")
    assert not b["metadata"]["device_accessible"]
    assert not s["metadata"]["device_accessible"]
    assert b["metadata"]["fictional_account"] == s["metadata"]["fictional_account"]
    assert audit["metrics"]["baseline"]["outcome"] == "handed_off"
    assert audit["metrics"]["stress"]["outcome"] == "unresolved"
    assert audit["metrics"]["baseline"]["usable_handoff"]
    assert not audit["metrics"]["stress"]["usable_handoff"]
    assert "MISSING_APPROVED_FALLBACK" in finding_types(audit, "stress")


def test_bounded_fallback_handoff_does_not_cause_missing_handoff_flag():
    audit = make("language_disparity")
    assert "MISSING_APPROVED_FALLBACK" not in finding_types(audit, "baseline")
    assert audit["metrics"]["baseline"]["escalation_compliant"]


def test_differences_appropriately_labeled():
    for scenario_id in SCENARIOS:
        audit = make(scenario_id)
        dimension = audit["comparison"]["dimension"]
        assert dimension == ("language" if scenario_id in {"control", "language_disparity"} else
                             "channel_access" if scenario_id == "digital_exclusion" else "recovery_path")
        assert audit["comparison"]["injected_scenario_not_real_world_prevalence"]
        assert audit["comparison"]["sample_size_per_path"] == 1


def test_cost_cad_config_explicitly_hypothetical():
    pricing = load_pricing()
    assert pricing["currency"] == "CAD"
    assert pricing["version"].startswith("hypothetical-cad")
    assert all(key.endswith("_cad_per_1m_tokens") or key in {"version", "currency", "notes", "model", "tool_call_cad"} for key in pricing)
    for scenario in SCENARIOS:
        a = make(scenario)
        assert a["currency"] == "CAD"
        assert all("hypothetical CAD" in a["metrics"][v]["cost_basis"] for v in ("baseline", "stress"))


def test_failed_task_need_not_cost_more_than_successful_task():
    audit = make("digital_exclusion")
    assert audit["metrics"]["stress"]["direct_execution_cost_cad"] < audit["metrics"]["baseline"]["direct_execution_cost_cad"]
    assert not audit["metrics"]["stress"]["safe_resolution"]


def test_avoidable_cost_only_for_evidence_linked_repetitions():
    audit = make("technical_outage")
    b, s = audit["metrics"]["baseline"], audit["metrics"]["stress"]
    assert b["potentially_avoidable_direct_cost_cad"] == 0
    assert 0 < s["potentially_avoidable_direct_cost_cad"] < s["direct_execution_cost_cad"]


def test_finding_evidence_ids_exist_and_refer_to_own_run():
    audit = make("language_disparity")
    event_sets = {r["run_id"]: {e["event_id"] for e in r["events"]} for r in audit["runs"]}
    for f in audit["findings"]:
        assert f["observed_evidence_ids"]
        assert set(f["observed_evidence_ids"]) <= event_sets[f["run_id"]]
        assert f["source"].startswith("deterministic")


def test_json_export_roundtrip_valid_schema():
    audit = make("language_disparity")
    payload = json.loads(audit_json(audit))
    assert [Run.from_dict(item).cohort_language for item in payload["runs"]] == ["en", "fr"]
    assert payload["schema_version"] == "0.2"


def test_csv_export_cad_and_variants():
    audit = make("technical_outage")
    payload = evidence_csv(audit).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(payload))
    rows = list(reader)
    assert rows and "cost_cad" in reader.fieldnames
    assert "cost_usd" not in reader.fieldnames
    assert {r["variant"] for r in rows} == {"baseline", "stress"}
    assert {r["language"] for r in rows} == {"en"}


def test_replay_fixtures_exist_and_re_evaluate():
    for scenario in SCENARIOS:
        a = load_fixture(scenario)
        assert a["mode"] == "trace_replay"
        assert a["scenario_id"] == scenario
        assert len(a["runs"]) == 2
        assert a["currency"] == "CAD"
        assert "fixture_provenance" in a


def test_import_recomputes_metrics_and_findings():
    audit = make("technical_outage")
    audit["metrics"]["stress"]["loop_count"] = 10**6
    audit["findings"] = []
    loaded = import_trace_json(json.dumps(audit))
    assert loaded["metrics"]["stress"]["loop_count"] == 2
    assert "AUTH_RETRY_LIMIT_EXCEEDED" in finding_types(loaded)
    assert loaded["mode"] == "trace_replay"


def test_import_rejects_sprint1_trace_instead_of_fake_conversion():
    audit = make("control")
    audit["runs"][0]["schema_version"] = "0.1"
    with pytest.raises(ValueError, match="schema"):
        import_trace_json(json.dumps(audit))


def test_import_rejects_invalid_language():
    audit = make("control")
    audit["runs"][0]["cohort_language"] = "es"
    with pytest.raises(ValueError):
        import_trace_json(json.dumps(audit))


def test_import_rejects_oversized_json():
    with pytest.raises(ValueError, match="2 MB"):
        import_trace_json("x" * 2_000_001)


def test_import_rejects_invalid_sequence():
    audit = make("technical_outage")
    audit["runs"][0]["events"][1]["sequence"] = 99
    with pytest.raises(ValueError, match="sequential"):
        import_trace_json(json.dumps(audit))


def test_wrong_pair_rejected():
    b = simulate_pair("digital_exclusion")[0]
    s = simulate_pair("digital_exclusion")[1]
    with pytest.raises(ValueError, match="different pair"):
        audit_pair([b, s])


def test_scenario_allowlist_and_retry_bounds():
    with pytest.raises(ValueError):
        simulate_pair("random_unknown")
    with pytest.raises(ValueError):
        simulate_pair("technical_outage", extra_retries=99)
    with pytest.raises(ValueError):
        simulate_pair("digital_exclusion", extra_retries=-1)


def test_database_saves_reviews(tmp_path):
    db = tmp_path / "audit.sqlite3"
    audit = make("digital_exclusion")
    save_audit(audit, db)
    assert load_audit(audit["pair_id"], db)["currency"] == "CAD"
    assert list_audits(db)[0]["scenario_id"] == "digital_exclusion"
    fid = audit["findings"][0]["finding_id"]
    save_review(audit["pair_id"], fid, "needs_investigation", "Check policy", db)
    assert list_reviews(audit["pair_id"], db)[0]["decision"] == "needs_investigation"
    save_audit(audit, db)  # foreign key stable even when audit is re-saved
    assert len(list_reviews(audit["pair_id"], db)) == 1


def test_review_rejects_unknown_finding(tmp_path):
    db = tmp_path / "audit.sqlite3"
    audit = make("technical_outage")
    save_audit(audit, db)
    with pytest.raises(ValueError, match="not part"):
        save_review(audit["pair_id"], "fabricated-id", "approved", "", db)


def test_no_live_agent_and_no_real_customer_secrets():
    blob = audit_json(make("digital_exclusion"))
    assert b"synthetic" in blob.lower()
    assert b"TEST-ACCOUNT-001" in blob
    assert b"private_key" not in blob.lower()
    assert b"password" not in blob.lower()
    assert b"secret" not in blob.lower()


def test_policy_has_french_equivalence_and_bounded_auth():
    policy = load_policy()
    assert policy["max_auth_attempts"] == 2
    assert "French" in policy["policy_rules"]["EQUIVALENT_APPROVED_FALLBACK"]


def test_import_rejects_claimed_completion_without_successful_recovery():
    audit = make("control")
    for event in audit["runs"][0]["events"]:
        if event["event_type"] == "tool_result" and event["tool_name"] == "request_recovery":
            event["status"] = "error"
            event["error_code"] = "RECOVERY_FAILED"
    with pytest.raises(ValueError, match="lacks verified successful recovery"):
        import_trace_json(json.dumps(audit))


def test_import_rejects_handoff_claim_without_usable_handoff():
    audit = make("language_disparity")
    for event in audit["runs"][0]["events"]:
        if event["event_type"] == "tool_result" and event["tool_name"] == "create_human_escalation":
            event["status"] = "error"
    with pytest.raises(ValueError, match="lacks successful usable escalation"):
        import_trace_json(json.dumps(audit))


def test_policy_refs_are_specific_to_scenario():
    for scenario in ("technical_outage", "digital_exclusion", "language_disparity"):
        audit = make(scenario)
        fallback = next(f for f in audit["findings"]
                        if f["variant"] == "stress" and f["finding_type"] == "MISSING_APPROVED_FALLBACK")
        if scenario == "technical_outage":
            assert fallback["policy_rule_ids"] == ["AUTH_OUTAGE_BOUNDED_RETRIES"]
        else:
            assert "AUTH_OUTAGE_BOUNDED_RETRIES" not in fallback["policy_rule_ids"]
        if scenario == "language_disparity":
            assert "EQUIVALENT_APPROVED_FALLBACK" in fallback["policy_rule_ids"]


def test_customer_prompts_not_misrepresented_as_completed_actions():
    for scenario in SCENARIOS:
        audit = make(scenario)
        for v in ("baseline", "stress"):
            metrics = audit["metrics"][v]
            assert metrics["customer_prompts_requested"] == metrics["customer_actions"]
            assert metrics["confirmed_customer_actions"] is None
            assert metrics["authentication_failure_count"] <= metrics["authentication_attempt_count"]
            assert metrics["authentication_over_limit_count"] <= metrics["authentication_failure_count"]


def test_json_export_includes_human_review_with_clear_meaning():
    audit = make("digital_exclusion")
    f = audit["findings"][0]
    reviews = [{"finding_id": f["finding_id"], "decision": "approved", "comment": "Confirmed", "timestamp_utc": "2026-11-06T00:00:00Z"}]
    exported = json.loads(audit_json_with_reviews(audit, reviews))
    assert exported["human_reviews"] == reviews
    assert "does not approve remediation" in exported["review_decision_semantics"]["approved"]
    assert exported["runs"] == audit["runs"]


def test_over_limit_count_scenario_a_matches_extra_retries():
    base = make("technical_outage", retries=0)
    extra = make("technical_outage", retries=2)
    assert base["metrics"]["stress"]["authentication_over_limit_count"] == 2
    assert extra["metrics"]["stress"]["authentication_over_limit_count"] == 4
    assert extra["comparison"]["deltas_stress_minus_baseline"]["customer_prompts_requested"] == 0
