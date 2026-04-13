"""
DB router: CRUD for pipeline run history.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db as _db

router = APIRouter(prefix="/api/db", tags=["db"])


class SaveRunRequest(BaseModel):
    celeb: str
    items: list
    blog_post: str
    title: str = ""


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/check")
async def check_recent(celeb: str, days: int = 7):
    run = await asyncio.to_thread(_db.check_recent_run, celeb, days)
    return {"found": run is not None, "run": run}


@router.get("/runs")
async def list_runs():
    runs = await asyncio.to_thread(_db.list_runs)
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = await asyncio.to_thread(_db.get_run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    ok = await asyncio.to_thread(_db.delete_run, run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"deleted": True}


@router.post("/runs")
async def save_run(req: SaveRunRequest):
    run_id = await asyncio.to_thread(
        _db.save_run, req.celeb, req.items, req.blog_post, req.title
    )
    return {"id": run_id}
