"""Blog source registry: CRUD endpoints for managing scrape sources."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.schemas import BlogSource, BlogSourceCreate, BlogSourceUpdate
import db as _db

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[BlogSource])
def list_sources():
    rows = _db.list_sources()
    return [BlogSource(**{**r, "active": bool(r.get("active", 1))}) for r in rows]


@router.post("", response_model=BlogSource, status_code=201)
def create_source(body: BlogSourceCreate):
    try:
        row = _db.create_source(
            name=body.name,
            url=body.url,
            image_mapping=body.image_mapping,
            active=body.active,
            notes=body.notes,
        )
    except Exception as e:
        # UNIQUE constraint on url
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="이미 등록된 URL입니다.")
        raise HTTPException(status_code=500, detail=str(e))
    return BlogSource(**{**row, "active": bool(row.get("active", 1))})


@router.put("/{source_id}", response_model=BlogSource)
def update_source(source_id: str, body: BlogSourceUpdate):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="변경할 필드가 없습니다.")
    ok = _db.update_source(source_id, **fields)
    if not ok:
        raise HTTPException(status_code=404, detail="소스를 찾을 수 없습니다.")
    row = _db.get_source(source_id)
    return BlogSource(**{**row, "active": bool(row.get("active", 1))})


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: str):
    ok = _db.delete_source(source_id)
    if not ok:
        raise HTTPException(status_code=404, detail="소스를 찾을 수 없습니다.")
