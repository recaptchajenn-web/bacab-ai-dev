"""Config loading independent of current working directory."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]


def load_policy() -> dict:
    return json.loads((ROOT / "config" / "policy.json").read_text(encoding="utf-8"))


def load_pricing() -> dict:
    return json.loads((ROOT / "config" / "pricing.json").read_text(encoding="utf-8"))
