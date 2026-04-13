"""
SQLite persistence layer.

Tables
------
scraped_posts    Per-post scraping cache  (post_url + content_hash)
extracted_items  LLM extraction cache     (post_url + content_hash)
celeb_items      Core data store          (연예인·제품·이미지·쿠팡URL)
pipeline_runs    Final blog post history
"""
from __future__ import annotations

import hashlib, json, os, sqlite3, uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline_runs.db")

_DDL = """
-- ── 0. Blog source registry ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blog_sources (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL DEFAULT '',
    url              TEXT NOT NULL UNIQUE,
    image_mapping    TEXT NOT NULL DEFAULT '두괄식',
    active           INTEGER NOT NULL DEFAULT 1,
    notes            TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL,
    last_scraped_at  TEXT
);

-- ── 1. Scraped-post cache ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scraped_posts (
    id           TEXT PRIMARY KEY,
    post_url     TEXT NOT NULL,
    post_title   TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    scraped_at   TEXT NOT NULL,
    raw_json     TEXT NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scraped_url_hash
    ON scraped_posts (post_url, content_hash);
CREATE INDEX IF NOT EXISTS idx_scraped_url
    ON scraped_posts (post_url);

-- ── 2. LLM extraction cache ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS extracted_items (
    id           TEXT PRIMARY KEY,
    post_url     TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    items_json   TEXT NOT NULL DEFAULT '[]'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_extracted_url_hash
    ON extracted_items (post_url, content_hash);

-- ── 3. Core celeb-item store ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS celeb_items (
    id            TEXT PRIMARY KEY,
    post_url      TEXT NOT NULL,
    post_title    TEXT NOT NULL DEFAULT '',
    celeb         TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT '',
    product_name  TEXT NOT NULL DEFAULT '',
    keywords_json TEXT NOT NULL DEFAULT '[]',
    image_url     TEXT NOT NULL DEFAULT '',
    coupang_url   TEXT NOT NULL DEFAULT '',
    raw_json      TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_celeb_items_celeb
    ON celeb_items (celeb, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_celeb_items_post
    ON celeb_items (post_url);

-- ── 4. Pipeline run history ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id            TEXT PRIMARY KEY,
    celeb         TEXT NOT NULL,
    celeb_key     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    title         TEXT NOT NULL DEFAULT '',
    items_json    TEXT NOT NULL DEFAULT '[]',
    blog_post     TEXT NOT NULL DEFAULT '',
    elements_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_celeb_key
    ON pipeline_runs (celeb_key, created_at DESC);
"""


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(_DDL)
        # Migrations — each ALTER TABLE is idempotent (silently ignored if column exists)
        for stmt in [
            "ALTER TABLE pipeline_runs ADD COLUMN elements_json TEXT NOT NULL DEFAULT '[]'",
        ]:
            try:
                conn.execute(stmt)
            except Exception:
                pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _celeb_key(celeb: str) -> str:
    return celeb.strip().lower()


def content_hash(data) -> str:
    """SHA-256 of the JSON-serialised data (dict/list/str)."""
    if isinstance(data, str):
        raw = data
    else:
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Blog source registry ─────────────────────────────────────────────────────

def _normalise_source_url(url: str) -> str:
    """Strip trailing slash and normalise mobile → desktop for Naver."""
    url = url.rstrip("/")
    url = url.replace("://m.blog.naver.com/", "://blog.naver.com/")
    return url


def list_sources() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM blog_sources ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_source(source_id: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM blog_sources WHERE id=?", (source_id,)
        ).fetchone()
    return dict(row) if row else None


def create_source(name: str, url: str, image_mapping: str = "두괄식",
                  active: bool = True, notes: str = "") -> dict:
    sid = uuid.uuid4().hex[:12]
    url = _normalise_source_url(url)
    now = _now()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO blog_sources "
            "(id, name, url, image_mapping, active, notes, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (sid, name, url, image_mapping, 1 if active else 0, notes, now),
        )
    return {"id": sid, "name": name, "url": url, "image_mapping": image_mapping,
            "active": active, "notes": notes, "created_at": now, "last_scraped_at": None}


def update_source(source_id: str, **fields) -> bool:
    if "url" in fields:
        fields["url"] = _normalise_source_url(fields["url"])
    if "active" in fields:
        fields["active"] = 1 if fields["active"] else 0
    if not fields:
        return False
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [source_id]
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            f"UPDATE blog_sources SET {set_clause} WHERE id=?", values
        )
    return cur.rowcount > 0


def delete_source(source_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM blog_sources WHERE id=?", (source_id,))
    return cur.rowcount > 0


def touch_source_scraped(source_id: str) -> None:
    """Update last_scraped_at to now."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE blog_sources SET last_scraped_at=? WHERE id=?",
            (_now(), source_id),
        )


def get_source_for_post_url(post_url: str) -> Optional[dict]:
    """Return the blog_sources row whose url is a prefix of post_url, or None."""
    normalised = _normalise_source_url(post_url)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM blog_sources WHERE active=1"
        ).fetchall()
    for row in rows:
        src_url = row["url"].rstrip("/")
        if normalised.startswith(src_url):
            return dict(row)
    return None


# ── Scraped-post cache ────────────────────────────────────────────────────────

def get_scraped_post(post_url: str, chash: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM scraped_posts WHERE post_url=? AND content_hash=?",
            (post_url, chash),
        ).fetchone()
    if not row:
        return None
    try:
        raw = json.loads(row["raw_json"])
    except Exception:
        raw = {}
    return {"id": row["id"], "post_url": row["post_url"],
            "post_title": row["post_title"], "content_hash": row["content_hash"],
            "scraped_at": row["scraped_at"], "raw": raw}


def save_scraped_post(post_url: str, post_title: str, chash: str, raw: dict) -> str:
    rid = uuid.uuid4().hex[:12]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scraped_posts "
            "(id, post_url, post_title, content_hash, scraped_at, raw_json) "
            "VALUES (?,?,?,?,?,?)",
            (rid, post_url, post_title, chash, _now(),
             json.dumps(raw, ensure_ascii=False)),
        )
    return rid


def list_scraped_posts() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, post_url, post_title, content_hash, scraped_at "
            "FROM scraped_posts ORDER BY scraped_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_scraped_post(pid: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM scraped_posts WHERE id=?", (pid,))
    return cur.rowcount > 0


# ── LLM extraction cache ──────────────────────────────────────────────────────

def get_extracted_items(post_url: str, chash: str) -> Optional[list]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT items_json FROM extracted_items "
            "WHERE post_url=? AND content_hash=?",
            (post_url, chash),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["items_json"])
    except Exception:
        return None


def save_extracted_items(post_url: str, chash: str, items: list) -> str:
    rid = uuid.uuid4().hex[:12]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO extracted_items "
            "(id, post_url, content_hash, extracted_at, items_json) "
            "VALUES (?,?,?,?,?)",
            (rid, post_url, chash, _now(),
             json.dumps(items, ensure_ascii=False)),
        )
    return rid


# ── Core celeb-item store ─────────────────────────────────────────────────────

def save_celeb_items(items: list[dict]) -> int:
    """Upsert a batch of CelebItem dicts. Returns number saved."""
    saved = 0
    with sqlite3.connect(DB_PATH) as conn:
        for it in items:
            rid = uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT OR REPLACE INTO celeb_items "
                "(id, post_url, post_title, celeb, category, product_name, "
                " keywords_json, image_url, coupang_url, raw_json, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rid,
                    it.get("source_url", ""),
                    it.get("source_title", ""),
                    it.get("celeb", ""),
                    it.get("category", ""),
                    it.get("product_name", ""),
                    json.dumps(it.get("keywords", []), ensure_ascii=False),
                    # store original network URL (first of image_urls before processing)
                    it.get("image_url", it.get("image_urls", [""])[0] if it.get("image_urls") else ""),
                    it.get("link_url", ""),
                    json.dumps(it, ensure_ascii=False),
                    _now(),
                ),
            )
            saved += 1
    return saved


def list_celeb_items(celeb: str = "", limit: int = 500) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if celeb:
            rows = conn.execute(
                "SELECT id, post_url, post_title, celeb, category, product_name, "
                "keywords_json, image_url, coupang_url, created_at "
                "FROM celeb_items WHERE celeb LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                (f"%{celeb}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, post_url, post_title, celeb, category, product_name, "
                "keywords_json, image_url, coupang_url, created_at "
                "FROM celeb_items ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["keywords"] = json.loads(d.pop("keywords_json"))
        except Exception:
            d["keywords"] = []
        result.append(d)
    return result


def delete_celeb_item(item_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM celeb_items WHERE id=?", (item_id,))
    return cur.rowcount > 0


def delete_celeb_items_by_post(post_url: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM celeb_items WHERE post_url=?", (post_url,))
    return cur.rowcount


# ── Pipeline run history ──────────────────────────────────────────────────────

def save_run(celeb: str, items: list[dict], blog_post: str,
             title: str = "", elements: list[dict] | None = None) -> str:
    run_id = uuid.uuid4().hex[:12]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO pipeline_runs "
            "(id, celeb, celeb_key, created_at, title, items_json, blog_post, elements_json) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                run_id, celeb.strip(), _celeb_key(celeb),
                _now(), title,
                json.dumps(items, ensure_ascii=False),
                blog_post,
                json.dumps(elements or [], ensure_ascii=False),
            ),
        )
    return run_id


def list_runs() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, celeb, created_at, title, items_json "
            "FROM pipeline_runs ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for row in rows:
        try:
            item_count = len(json.loads(row["items_json"]))
        except Exception:
            item_count = 0
        result.append({
            "id": row["id"], "celeb": row["celeb"],
            "created_at": row["created_at"], "title": row["title"],
            "item_count": item_count,
        })
    return result


def get_run(run_id: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE id=?", (run_id,)
        ).fetchone()
    if not row:
        return None
    try:
        items = json.loads(row["items_json"])
    except Exception:
        items = []
    try:
        elements = json.loads(row["elements_json"])
    except Exception:
        elements = []
    return {
        "id": row["id"], "celeb": row["celeb"],
        "created_at": row["created_at"], "title": row["title"],
        "item_count": len(items), "items": items,
        "blog_post": row["blog_post"], "elements": elements,
    }


def delete_run(run_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM pipeline_runs WHERE id=?", (run_id,))
    return cur.rowcount > 0


def check_recent_run(celeb: str, days: int = 7) -> Optional[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM pipeline_runs "
            "WHERE celeb_key=? AND created_at>=? "
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
        "id": row["id"], "celeb": row["celeb"],
        "created_at": row["created_at"], "title": row["title"],
        "item_count": len(items), "items": items,
        "blog_post": row["blog_post"], "days_ago": days_ago,
    }
