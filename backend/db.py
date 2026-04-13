"""
SQLite persistence layer for pipeline runs.
Uses Python stdlib sqlite3 — no extra dependencies.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline_runs.db")

_DDL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          TEXT PRIMARY KEY,
    celeb       TEXT NOT NULL,
    celeb_key   TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    items_json  TEXT NOT NULL DEFAULT '[]',
    blog_post   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_celeb_key ON pipeline_runs (celeb_key, created_at DESC);
"""


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(_DDL)


def _celeb_key(celeb: str) -> str:
    return celeb.strip().lower()


def save_run(celeb: str, items: list[dict], blog_post: str, title: str = "") -> str:
    run_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO pipeline_runs (id, celeb, celeb_key, created_at, title, items_json, blog_post) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, celeb.strip(), _celeb_key(celeb),
             now, title, json.dumps(items, ensure_ascii=False), blog_post),
        )
    return run_id


def list_runs() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, celeb, created_at, title, items_json FROM pipeline_runs "
            "ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for row in rows:
        try:
            item_count = len(json.loads(row["items_json"]))
        except Exception:
            item_count = 0
        result.append({
            "id": row["id"],
            "celeb": row["celeb"],
            "created_at": row["created_at"],
            "title": row["title"],
            "item_count": item_count,
        })
    return result


def get_run(run_id: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)
        ).fetchone()
    if not row:
        return None
    try:
        items = json.loads(row["items_json"])
    except Exception:
        items = []
    return {
        "id": row["id"],
        "celeb": row["celeb"],
        "created_at": row["created_at"],
        "title": row["title"],
        "item_count": len(items),
        "items": items,
        "blog_post": row["blog_post"],
    }


def delete_run(run_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM pipeline_runs WHERE id = ?", (run_id,))
    return cur.rowcount > 0


def check_recent_run(celeb: str, days: int = 7) -> Optional[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM pipeline_runs "
            "WHERE celeb_key = ? AND created_at >= ? "
            "ORDER BY created_at DESC LIMIT 1",
            (_celeb_key(celeb), cutoff),
        ).fetchone()
    if not row:
        return None
    try:
        items = json.loads(row["items_json"])
    except Exception:
        items = []

    created = datetime.fromisoformat(row["created_at"])
    days_ago = (datetime.now(timezone.utc) - created).days

    return {
        "id": row["id"],
        "celeb": row["celeb"],
        "created_at": row["created_at"],
        "title": row["title"],
        "item_count": len(items),
        "items": items,
        "blog_post": row["blog_post"],
        "days_ago": days_ago,
    }
