"""Capture deterministic redacted test evidence; no secret, prompt, or OTP content."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .schema import Event, Run, new_id
from .config import load_pricing


class TraceCollector:
    def __init__(self, run: Run):
        self.run = run
        self._timestamp = datetime.now(timezone.utc) if run.mode == "live_openai" else datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
        self._prices = load_pricing()

    def emit(self, actor: str, event_type: str, duration_ms: int = 0, **kwargs) -> Event:
        self._timestamp = (datetime.now(timezone.utc) if self.run.mode == "live_openai"
                           else self._timestamp + timedelta(milliseconds=max(0, duration_ms)))
        event = Event(event_id=new_id("evt"), run_id=self.run.run_id, pair_id=self.run.pair_id,
                      scenario_id=self.run.scenario_id, variant=self.run.variant,
                      cohort_language=self.run.cohort_language,
                      timestamp_utc=self._timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                      sequence=len(self.run.events) + 1, actor=actor, event_type=event_type,
                      duration_ms=duration_ms, **kwargs)
        event.validate()
        self.run.events.append(event)
        return event

    def model_decision(self, note: str, *, tool_call_id: str | None = None) -> Event:
        inp, out = 110, 38
        price = (inp * self._prices["input_cad_per_1m_tokens"] +
                 out * self._prices["output_cad_per_1m_tokens"]) / 1_000_000
        return self.emit("subject_agent", "llm_response", duration_ms=160,
                         tool_call_id=tool_call_id,
                         input_tokens=inp, output_tokens=out, cost_cad=price,
                         metadata={"model": "synthetic-sandbox-model", "decision_label": note,
                                   "usage_source": "hypothetical_simulation",
                                   "linked_tool_call_ids": [tool_call_id] if tool_call_id else [],
                                   "initiated_by": "scripted_simulation"})

    def tool(self, bank, name: str, call, *, duration_ms: int = 95,
             fault_injected: bool = False, customer_action_required: bool = False,
             rule_ids: list[str] | None = None) -> Event:
        """Perform a local Python tool call, emitting call/result linked by tool_call_id."""
        call_id = new_id("call")
        self.model_decision(f"invoke:{name}", tool_call_id=call_id)
        before = bank.verified
        self.emit("subject_agent", "tool_call", tool_name=name, tool_call_id=call_id,
                  verification_valid_before=before, verification_valid_after=before,
                  metadata={"sandbox_tool": True, "initiated_by": "scripted_simulation"})
        result = call()
        return self.emit("tool", "tool_result", tool_name=name, tool_call_id=call_id,
                         duration_ms=duration_ms, status=result["status"],
                         error_code=result.get("error_code"),
                         attempt=(bank.auth_attempts if name == "verify_one_time_code" else
                                  bank.recovery_attempts if name == "request_recovery" else
                                  bank.verification_requests if name == "request_verification" else None),
                         verification_valid_before=before,
                         verification_valid_after=bank.verified,
                         customer_action_required=customer_action_required,
                         policy_rule_ids=rule_ids or [],
                         cost_cad=self._prices["tool_call_cad"],
                         metadata={"fault_injected": fault_injected,
                                   "initiated_by": "scripted_simulation",
                                   "result_flags": {k: v for k, v in result.items()
                                                    if k in {"verified", "usable_handoff", "recovery_issued", "channel_usable"}},
                                   "usage_source": "hypothetical_simulation"})
