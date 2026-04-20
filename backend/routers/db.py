"""DB CRUD endpoints: pipeline runs, celeb items, scraped-post cache."""
from __future__ import annotations
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import db as _db

router = APIRouter(prefix="/api/db", tags=["db"])


# ── Pipeline run history ──────────────────────────────────────────────────────

class SaveRunRequest(BaseModel):
    celeb: str
    items: list
    blog_post: str
    title: str = ""
    elements: list = []


@router.get("/check")
async def check_recent(celeb: str, days: int = 7):
    run = await asyncio.to_thread(_db.check_recent_run, celeb, days)
    return {"found": run is not None, "run": run}


@router.get("/runs")
async def list_runs():
    return {"runs": await asyncio.to_thread(_db.list_runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = await asyncio.to_thread(_db.get_run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    ok = await asyncio.to_thread(_db.delete_run, run_id)
    if not ok:
        raise HTTPException(404, "Run not found")
    return {"deleted": True}


@router.post("/runs")
async def save_run(req: SaveRunRequest):
    rid = await asyncio.to_thread(
        _db.save_run, req.celeb, req.items, req.blog_post, req.title, req.elements
    )
    return {"id": rid}


# ── Celeb item store ──────────────────────────────────────────────────────────

@router.get("/celeb-items")
async def list_celeb_items(celeb: str = "", limit: int = 500):
    items = await asyncio.to_thread(_db.list_celeb_items, celeb, limit)
    return {"items": items}


@router.delete("/celeb-items/{item_id}")
async def delete_celeb_item(item_id: str):
    ok = await asyncio.to_thread(_db.delete_celeb_item, item_id)
    if not ok:
        raise HTTPException(404, "Item not found")
    return {"deleted": True}


@router.delete("/celeb-items-by-post")
async def delete_celeb_items_by_post(post_url: str):
    count = await asyncio.to_thread(_db.delete_celeb_items_by_post, post_url)
    return {"deleted": count}


# ── Scraped-post cache ────────────────────────────────────────────────────────

@router.get("/scraped-posts")
async def list_scraped_posts():
    posts = await asyncio.to_thread(_db.list_scraped_posts)
    return {"posts": posts}


@router.delete("/scraped-posts/{post_id}")
async def delete_scraped_post(post_id: str):
    ok = await asyncio.to_thread(_db.delete_scraped_post, post_id)
    if not ok:
        raise HTTPException(404, "Post not found")
    return {"deleted": True}
