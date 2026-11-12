"""Plan B: independently re-evaluate validated synthetic/third-party trace JSON.

Does not execute imported content. Sprint 1's v0.1 EN/ES/USD exports are intentionally
rejected rather than silently converting their units or altering their evidence.
"""
from __future__ import annotations
from pathlib import Path
import json
from .config import load_policy
from .schema import Run
from .evaluators import audit_pair
from .config import ROOT
from .scenarios import SCENARIOS

FIXTURES_PATH = ROOT / "fixtures"
MAX_IMPORT_CHARS = 2_000_000


def load_fixture(scenario_id: str) -> dict:
    if scenario_id not in SCENARIOS:
        raise ValueError("Scenario not in allowlist")
    path = FIXTURES_PATH / f"{scenario_id}.json"
    return _from_json(path.read_text(encoding="utf-8"), f"Bundled synthetic fixture: {path.name}")


def import_trace_json(raw_json: str) -> dict:
    return _from_json(raw_json, "User-supplied trace JSON (validated; never executed)")


def _from_json(raw_json: str, provenance: str) -> dict:
    if len(raw_json) > MAX_IMPORT_CHARS:
        raise ValueError("Trace exceeds 2 MB import limit")
    def reject_nonfinite(value: str):
        raise ValueError(f"Non-finite JSON value {value} is not allowed in audit evidence")
    parsed = json.loads(raw_json, parse_constant=reject_nonfinite)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("runs"), list) or len(parsed["runs"]) != 2:
        raise ValueError("Expected a JSON object containing exactly two runs")
    runs = [Run.from_dict(item) for item in parsed["runs"]]
    current_policy = load_policy()["version"]
    if any(run.policy_version != current_policy for run in runs):
        raise ValueError("Imported trace policy version differs from the configured audit policy; do not silently re-evaluate under another rulebook")
    if any(len(run.events) > 1000 for run in runs):
        raise ValueError("Trace exceeds 1,000 events per run")
    for run in runs:
        run.mode = "trace_replay"
    # Never trust metrics/findings embedded in an imported document: recompute.
    audit = audit_pair(runs)
    audit["fixture_provenance"] = provenance
    return audit
