"""Sprint 2.7.1 narrow security hotfix acceptance, entirely offline."""
from __future__ import annotations
import csv
import io
import json
import math

import pytest

from bacab_core.evaluators import audit_pair
from bacab_core.replay import import_trace_json
from bacab_core.reporting import evidence_csv
from bacab_core.scenarios import simulate_pair
from bacab_core.storage import save_audit, load_audit, list_audits, save_review, list_reviews


def make(scenario="technical_outage"):
    return audit_pair(simulate_pair(scenario))


def test_original_audit_remains_immutable_after_import_of_same_pair(tmp_path):
    db = tmp_path / "bacab.sqlite3"
    original = make()
    original["mode"] = "live_openai"  # storage identity test; not an API call
    replay = import_trace_json(json.dumps(original))
    key_original = save_audit(original, db)
    key_replay = save_audit(replay, db)
    assert key_original == original["pair_id"]
    assert key_replay != key_original
    assert load_audit(key_original, db) == original
    assert load_audit(key_replay, db) == replay
    assert {x["mode"] for x in list_audits(db)} == {"live_openai", "trace_replay"}
    assert all(x["pair_id"] in {key_original, key_replay} for x in list_audits(db))
    assert replay["pair_id"] == original["pair_id"]  # canonical source ID unchanged


def test_review_decisions_isolated_between_original_and_replay(tmp_path):
    db = tmp_path / "history.sqlite3"
    original = make()
    replay = import_trace_json(json.dumps(original))
    original_key = save_audit(original, db)
    replay_key = save_audit(replay, db)
    finding_id = original["findings"][0]["finding_id"]
    save_review(original_key, finding_id, "approved", "original review", db)
    save_review(replay_key, finding_id, "rejected", "replay review", db)
    assert list_reviews(original_key, db)[0]["comment"] == "original review"
    assert list_reviews(replay_key, db)[0]["comment"] == "replay review"
    assert save_audit(original, db) == original_key  # identical re-save is safe
    assert len(list_reviews(original_key, db)) == 1


def test_import_export_csv_escapes_injected_formula_without_changing_json():
    original = make()
    original["runs"][1]["events"][0]["event_id"] = "=HYPERLINK(\"https://example.invalid\",\"click\")"
    replay = import_trace_json(json.dumps(original))
    out = evidence_csv(replay).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(out)))
    assert rows[0]["event_id"] != original["runs"][1]["events"][0]["event_id"]  # earlier baseline row
    injected = [r for r in rows if r["event_id"].startswith("'=HYPERLINK")]
    assert len(injected) == 1
    assert replay["runs"][1]["events"][0]["event_id"].startswith("=HYPERLINK")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_replay_rejects_nonfinite_costs(bad):
    original = make()
    next(e for e in original["runs"][1]["events"] if e["event_type"] == "tool_result")["cost_cad"] = bad
    with pytest.raises(ValueError, match="Non-finite"):
        import_trace_json(json.dumps(original))


def test_replay_rejects_nonfinite_numeric_cost_with_json_exponent():
    original = make()
    payload = json.dumps(original)
    payload = payload.replace('"cost_cad": 0.0014', '"cost_cad": 1e999', 1)
    with pytest.raises(ValueError, match="Invalid CAD event cost"):
        import_trace_json(payload)


def test_replay_rejects_mismatched_policy_version():
    original = make()
    for run in original["runs"]:
        run["policy_version"] = "bank-recovery-v1"
    with pytest.raises(ValueError, match="policy version"):
        import_trace_json(json.dumps(original))


def test_replay_all_three_scenarios_preserve_cost_outcome_and_event_ids():
    for scenario in ["technical_outage", "digital_exclusion", "language_disparity"]:
        original = make(scenario)
        replay = import_trace_json(json.dumps(original))
        assert replay["mode"] == "trace_replay"
        assert [run["events"] for run in original["runs"]] == [run["events"] for run in replay["runs"]]
        for variant in ("baseline", "stress"):
            assert replay["metrics"][variant]["direct_execution_cost_cad"] == original["metrics"][variant]["direct_execution_cost_cad"]
            assert replay["metrics"][variant]["outcome"] == original["metrics"][variant]["outcome"]
        assert {f["finding_type"] for f in replay["findings"]} == {f["finding_type"] for f in original["findings"]}
