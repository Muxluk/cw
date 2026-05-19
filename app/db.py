from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator

from app.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_value TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                input_path TEXT,
                normalized_path TEXT,
                result_path TEXT,
                meta_json TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def utcnow() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_job(job: dict[str, Any]) -> None:
    payload = {
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "meta_json": json.dumps(job.get("meta_json")) if job.get("meta_json") is not None else None,
        "result_json": json.dumps(job.get("result_json")) if job.get("result_json") is not None else None,
        **job,
    }
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, source_type, source_value, status, message,
                input_path, normalized_path, result_path, meta_json, result_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload["source_type"],
                payload["source_value"],
                payload["status"],
                payload["message"],
                payload.get("input_path"),
                payload.get("normalized_path"),
                payload.get("result_path"),
                payload.get("meta_json"),
                payload.get("result_json"),
                payload["created_at"],
                payload["updated_at"],
            ),
        )
        conn.commit()


def update_job(job_id: str, **fields: Any) -> None:
    if "meta_json" in fields and fields["meta_json"] is not None:
        fields["meta_json"] = json.dumps(fields["meta_json"], ensure_ascii=False)
    if "result_json" in fields and fields["result_json"] is not None:
        fields["result_json"] = json.dumps(fields["result_json"], ensure_ascii=False)
    fields["updated_at"] = utcnow()

    columns = ", ".join(f"{key} = ?" for key in fields.keys())
    values = list(fields.values()) + [job_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE jobs SET {columns} WHERE id = ?", values)
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    if data.get("meta_json"):
        data["meta_json"] = json.loads(data["meta_json"])
    else:
        data["meta_json"] = None
    if data.get("result_json"):
        data["result_json"] = json.loads(data["result_json"])
    else:
        data["result_json"] = None
    return data
