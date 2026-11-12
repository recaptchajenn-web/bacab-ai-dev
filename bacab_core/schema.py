"""BACAB v0.2 canonical audit trace: one matched BASELINE / STRESS pair.

For technical/accessibility scenarios language is held constant; only the
language disparity stress test compares EN/FR. Never assert linguistic causality
for differences deliberately injected by the scenario designer.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
import uuid
from math import isfinite

SCHEMA_VERSION = "0.2"
ALLOWED_LANGUAGES = {"en", "fr"}
ALLOWED_VARIANTS = {"baseline", "stress"}
ALLOWED_EVENT_TYPES = {"tool_call", "tool_result", "llm_response", "outcome", "customer_message", "state_transition"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Event:
    event_id: str
    run_id: str
    pair_id: str
    scenario_id: str
    variant: str
    cohort_language: str
    timestamp_utc: str
    sequence: int
    actor: str
    event_type: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    status: str = "ok"
    error_code: str | None = None
    attempt: int | None = None
    duration_ms: int = 0
    verification_valid_before: bool | None = None
    verification_valid_after: bool | None = None
    customer_action_required: bool = False
    policy_rule_ids: list[str] = field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cad: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported event schema {self.schema_version!r}; Sprint 1 USD/ES traces require a separate migration")
        if self.cohort_language not in ALLOWED_LANGUAGES or self.variant not in ALLOWED_VARIANTS:
            raise ValueError("Unsupported language or comparison variant")
        if self.event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {self.event_type}")
        if self.sequence < 1 or self.duration_ms < 0:
            raise ValueError("Invalid event sequence or duration")
        for label, value in (("input_tokens", self.input_tokens), ("output_tokens", self.output_tokens)):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"Invalid {label}: token usage must be a nonnegative integer")
        if self.cost_cad is not None and (
            type(self.cost_cad) not in (int, float) or
            not isfinite(self.cost_cad) or self.cost_cad < 0
        ):
            raise ValueError("Invalid CAD event cost: must be a finite nonnegative number")
        if self.event_type in {"tool_call", "tool_result"} and not self.tool_name:
            raise ValueError("Tool events require tool_name")
        if not self.event_id or not self.run_id or not self.pair_id:
            raise ValueError("Missing event/run/pair ID")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        unknown = set(data) - cls.__dataclass_fields__.keys()
        if unknown:
            raise ValueError(f"Unsupported event keys: {sorted(unknown)}")
        event = cls(**data)
        event.validate()
        return event


@dataclass
class Run:
    run_id: str
    pair_id: str
    scenario_id: str
    cohort_language: str
    variant: str
    mode: str
    policy_version: str
    events: list[Event] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.cohort_language not in ALLOWED_LANGUAGES or self.variant not in ALLOWED_VARIANTS:
            raise ValueError("Invalid run schema, language, or variant. Sprint 1 traces are not compatible without migration.")
        seen: set[str] = set()
        for i, event in enumerate(self.events, 1):
            event.validate()
            if (event.run_id, event.pair_id, event.scenario_id, event.variant, event.cohort_language) != (self.run_id, self.pair_id, self.scenario_id, self.variant, self.cohort_language):
                raise ValueError("Event does not match parent run")
            if event.sequence != i or event.event_id in seen:
                raise ValueError("Events must have sequential positions and unique IDs")
            seen.add(event.event_id)
        if not self.events or self.events[-1].event_type != "outcome":
            raise ValueError("A run must end with an outcome event")

    def to_dict(self) -> dict[str, Any]:
        return {**{k: v for k, v in asdict(self).items() if k != "events"},
                "events": [e.to_dict() for e in self.events]}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Run":
        data = dict(raw)
        data["events"] = [Event.from_dict(e) for e in raw["events"]]
        run = cls(**data)
        run.validate()
        return run
