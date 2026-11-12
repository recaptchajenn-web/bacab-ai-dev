"""Local SQLite audit trail and human-review decisions."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from uuid import uuid4
from .config import ROOT

DB_DEFAULT = ROOT / "data" / "bacab.sqlite3"


def connect(db_path: str | Path = DB_DEFAULT) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS audits (
            pair_id TEXT PRIMARY KEY,
            created_utc TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_id TEXT NOT NULL,
            finding_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('approved','rejected','needs_investigation')),
            comment TEXT NOT NULL,
            timestamp_utc TEXT NOT NULL,
            FOREIGN KEY(pair_id) REFERENCES audits(pair_id)
        );
    """)
    db.commit()
    return db


def save_audit(audit: dict, db_path: str | Path = DB_DEFAULT) -> str:
    """Save a distinct evaluation without overwriting earlier evidence.

    The legacy SQLite column is named pair_id, but for two evaluations of the
    *same trace pair* it holds a distinct storage-record ID. The unchanged
    canonical source pair ID always stays inside payload_json. Reviews are
    linked to the returned storage ID, not the reused canonical pair ID.
    No schema migration is needed for existing Windows installations.
    """
    serialized = json.dumps(audit, ensure_ascii=False, allow_nan=False)
    source_pair = audit["pair_id"]
    with connect(db_path) as db:
        existing = db.execute("SELECT payload_json FROM audits WHERE pair_id=?", (source_pair,)).fetchone()
        if existing is not None and existing[0] == serialized:
            # Idempotent re-save of the identical report is safe and preserves reviews.
            return source_pair
        record_id = source_pair if existing is None else "audit_" + uuid4().hex
        db.execute("INSERT INTO audits (pair_id, created_utc, scenario_id, mode, payload_json) VALUES (?, ?, ?, ?, ?)",
                   (record_id, datetime.now(timezone.utc).isoformat(),
                    audit["scenario_id"], audit["mode"], serialized))
    return record_id


def list_audits(db_path: str | Path = DB_DEFAULT) -> list[dict]:
    with connect(db_path) as db:
        rows = db.execute("SELECT pair_id, created_utc, scenario_id, mode FROM audits ORDER BY created_utc DESC LIMIT 100").fetchall()
    return [dict(zip(["pair_id", "created_utc", "scenario_id", "mode"], row)) for row in rows]


def load_audit(pair_id: str, db_path: str | Path = DB_DEFAULT) -> dict | None:
    with connect(db_path) as db:
        row = db.execute("SELECT payload_json FROM audits WHERE pair_id=?", (pair_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_review(pair_id: str, finding_id: str, decision: str, comment: str = "",
                db_path: str | Path = DB_DEFAULT) -> None:
    if decision not in {"approved", "rejected", "needs_investigation"}:
        raise ValueError("Invalid reviewer decision")
    audit = load_audit(pair_id, db_path)
    if audit is None or finding_id not in {f["finding_id"] for f in audit["findings"]}:
        raise ValueError("Finding is not part of this audit")
    with connect(db_path) as db:
        db.execute("INSERT INTO reviews (pair_id, finding_id, decision, comment, timestamp_utc) VALUES (?, ?, ?, ?, ?)",
                   (pair_id, finding_id, decision, comment[:2000], datetime.now(timezone.utc).isoformat()))


def list_reviews(pair_id: str, db_path: str | Path = DB_DEFAULT) -> list[dict]:
    with connect(db_path) as db:
        rows = db.execute("SELECT finding_id, decision, comment, timestamp_utc FROM reviews WHERE pair_id=? ORDER BY review_id DESC",
                          (pair_id,)).fetchall()
    return [dict(zip(["finding_id", "decision", "comment", "timestamp_utc"], row)) for row in rows]
