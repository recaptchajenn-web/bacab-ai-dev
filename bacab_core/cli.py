"""Smoke test: python -m bacab_core.cli demo --scenario digital_exclusion"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .scenarios import SCENARIOS, simulate_pair
from .evaluators import audit_pair
from .replay import load_fixture
from .storage import save_audit
from .reporting import audit_json


def main():
    parser = argparse.ArgumentParser(description="BACAB Recovery Equity audit (synthetic; no API key)")
    parser.add_argument("command", nargs="?", default="demo", choices=["demo", "replay"])
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="digital_exclusion")
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "replay" and args.retries:
        parser.error("--retries applies only to demo mode")
    audit = (audit_pair(simulate_pair(args.scenario, extra_retries=args.retries))
             if args.command == "demo" else load_fixture(args.scenario))
    if args.save:
        save_audit(audit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(audit_json(audit))
    print(json.dumps({"scenario": audit["scenario_id"], "mode": audit["mode"],
                      "pair_id": audit["pair_id"], "currency": audit["currency"],
                      "baseline": {k: audit["metrics"]["baseline"][k] for k in
                                   ("outcome", "customer_actions", "direct_execution_cost_cad")},
                      "stress": {k: audit["metrics"]["stress"][k] for k in
                                 ("outcome", "customer_actions", "direct_execution_cost_cad")},
                      "potential_recovery_equity_issue": audit["comparison"]["potential_recovery_equity_issue"],
                      "finding_types": [f["finding_type"] for f in audit["findings"]],
                      "saved": args.save}, indent=2))


if __name__ == "__main__":
    main()
