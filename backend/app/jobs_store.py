"""Tiny SQLite job store. Stores job metadata and outputs (not the raw source text)."""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import get_settings


def _conn() -> sqlite3.Connection:
    path = get_settings().database_path
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            mode TEXT,
            created_at TEXT,
            completed_at TEXT,
            source_chars INTEGER,
            output_types TEXT,
            settings TEXT,
            result TEXT
        )"""
    )
    return conn


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def create_job(job_id: str, mode: str, source_chars: int, output_types: list, settings: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO jobs (job_id,status,mode,created_at,source_chars,output_types,settings) VALUES (?,?,?,?,?,?,?)",
            (
                job_id,
                "running",
                mode,
                datetime.now(timezone.utc).isoformat(),
                source_chars,
                json.dumps(output_types),
                json.dumps(settings),
            ),
        )


def complete_job(job_id: str, status: str, result: Dict[str, Any]) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE jobs SET status=?, completed_at=?, result=? WHERE job_id=?",
            (status, datetime.now(timezone.utc).isoformat(), json.dumps(result), job_id),
        )


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["output_types"] = json.loads(d["output_types"] or "[]")
    d["settings"] = json.loads(d["settings"] or "{}")
    d["result"] = json.loads(d["result"]) if d.get("result") else None
    return d
