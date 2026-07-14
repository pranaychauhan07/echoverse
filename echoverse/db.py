"""Persistence layer for narration jobs and history.

SQLite today (zero setup, zero cost, file-based). The schema is plain
SQL on purpose so swapping the connection to a free-tier Postgres
(Supabase/Neon) later is a one-line change, not a rewrite.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "echoverse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,             -- queued | running | done | failed
    tone TEXT NOT NULL,
    source_text TEXT NOT NULL,
    rewritten_text TEXT,
    audio_path TEXT,
    transcript TEXT,
    qa_similarity REAL,
    qa_passed INTEGER,
    revision_log TEXT,                -- JSON
    metrics TEXT,                     -- JSON: per-stage timing + char counts (cost/latency dashboard data)
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(SCHEMA)
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        if "metrics" not in existing_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN metrics TEXT")


def create_job(source_text: str, tone: str) -> str:
    job_id = str(uuid.uuid4())
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs (id, status, tone, source_text, created_at, updated_at) "
            "VALUES (?, 'queued', ?, ?, ?, ?)",
            (job_id, tone, source_text, now, now),
        )
    return job_id


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    if "revision_log" in fields and not isinstance(fields["revision_log"], str):
        fields["revision_log"] = json.dumps(fields["revision_log"])
    if "metrics" in fields and not isinstance(fields["metrics"], str):
        fields["metrics"] = json.dumps(fields["metrics"])
    if "qa_passed" in fields:
        fields["qa_passed"] = int(bool(fields["qa_passed"]))

    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", (*fields.values(), job_id))


def get_job(job_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    with get_conn() as conn:
        totals = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done, "
            "SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, "
            "SUM(CASE WHEN qa_passed = 1 THEN 1 ELSE 0 END) AS qa_passed_count "
            "FROM jobs"
        ).fetchone()
        rows = conn.execute("SELECT metrics FROM jobs WHERE metrics IS NOT NULL").fetchall()

    total_chars_in = total_chars_out = total_seconds = total_revisions = total_tts_retries = 0
    n = 0
    for row in rows:
        m = json.loads(row["metrics"])
        total_chars_in += m.get("chars_in", 0)
        total_chars_out += m.get("chars_out", 0)
        total_seconds += m.get("stage_seconds", {}).get("total", 0)
        total_revisions += m.get("revision_attempts", 0)
        total_tts_retries += m.get("tts_retries", 0)
        n += 1

    return {
        "jobs_total": totals["total"] or 0,
        "jobs_done": totals["done"] or 0,
        "jobs_failed": totals["failed"] or 0,
        "audio_qa_pass_count": totals["qa_passed_count"] or 0,
        "total_chars_in": total_chars_in,
        "total_chars_out": total_chars_out,
        "avg_seconds_per_job": round(total_seconds / n, 2) if n else 0,
        "total_critic_revisions": total_revisions,
        "total_tts_retries": total_tts_retries,
        "note": "All processing is local/free today. This is the usage baseline "
                "to compare against once ElevenLabs or hosted inference is enabled.",
    }
