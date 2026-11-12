"""Fictional banking sandbox, no production API connections or OTP disclosure."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class MockBank:
    account_ref: str = "TEST-ACCOUNT-001"
    device_accessible: bool = True
    auth_api_available: bool = True
    verified: bool = False
    auth_attempts: int = 0
    recovery_attempts: int = 0
    verification_requests: int = 0
    escalation_created: bool = False

    def lookup_account(self) -> dict:
        return {"status": "ok", "account_eligible": True, "account_ref": self.account_ref}

    def request_verification(self) -> dict:
        self.verification_requests += 1
        if not self.device_accessible:
            return {"status": "error", "error_code": "CHANNEL_UNAVAILABLE", "channel_usable": False}
        return {"status": "ok", "verification_challenge_created": True, "channel_usable": True}

    def verify_one_time_code(self) -> dict:
        self.auth_attempts += 1
        if not self.auth_api_available:
            return {"status": "error", "error_code": "AUTH_API_UNAVAILABLE"}
        if not self.device_accessible:
            return {"status": "error", "error_code": "CHANNEL_UNAVAILABLE"}
        self.verified = True  # deterministic fictional test credential, no secret stored in trace
        return {"status": "ok", "verified": True}

    def request_recovery(self) -> dict:
        self.recovery_attempts += 1
        if not self.verified:
            return {"status": "error", "error_code": "NOT_VERIFIED"}
        return {"status": "ok", "recovery_issued": True}

    def create_human_escalation(self) -> dict:
        self.escalation_created = True
        return {"status": "ok", "usable_handoff": True, "ticket_ref": "TEST-TICKET-001"}
