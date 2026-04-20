"""Scheduler management endpoints (APScheduler)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from models.schemas import ScheduleJob, ScheduleJobCreate

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

# In-memory job store (persisted via APScheduler SQLite in main.py)
_jobs: dict[str, dict] = {}


def _get_scheduler():
    """Import scheduler from main to avoid circular imports."""
    from main import scheduler
    return scheduler


@router.get("/jobs", response_model=List[ScheduleJob])
async def list_jobs():
    sched = _get_scheduler()
    result: List[ScheduleJob] = []
    for job_id, meta in _jobs.items():
        apj = sched.get_job(job_id)
        next_run = None
        if apj and apj.next_run_time:
            next_run = apj.next_run_time.isoformat()
        result.append(ScheduleJob(
            id=job_id,
            name=meta["name"],
            cron=meta["cron"],
            enabled=meta.get("enabled", True),
            days=meta.get("days", 2),
            max_posts=meta.get("max_posts", 10),
            top_celebs=meta.get("top_celebs", 3),
            auto_publish=meta.get("auto_publish", False),
            last_run=meta.get("last_run"),
            next_run=next_run,
        ))
    return result


@router.post("/jobs", response_model=ScheduleJob)
async def create_job(req: ScheduleJobCreate):
    sched = _get_scheduler()
    job_id = str(uuid.uuid4())[:8]

    parts = req.cron.split()
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail="cron 형식: '분 시 일 월 요일' (예: '0 9 * * *')")

    minute, hour, day, month, day_of_week = parts

    from scheduler.tasks import run_pipeline_job
    apj = sched.add_job(
        run_pipeline_job,
        trigger="cron",
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
        id=job_id,
        args=[job_id],
        replace_existing=True,
    )
    if not req.enabled:
        apj.pause()

    _jobs[job_id] = {
        "name": req.name,
        "cron": req.cron,
        "enabled": req.enabled,
        "days": req.days,
        "max_posts": req.max_posts,
        "top_celebs": req.top_celebs,
        "auto_publish": req.auto_publish,
        "last_run": None,
    }

    return ScheduleJob(
        id=job_id,
        name=req.name,
        cron=req.cron,
        enabled=req.enabled,
        days=req.days,
        max_posts=req.max_posts,
        top_celebs=req.top_celebs,
        auto_publish=req.auto_publish,
        next_run=apj.next_run_time.isoformat() if apj.next_run_time else None,
    )


@router.put("/jobs/{job_id}", response_model=ScheduleJob)
async def update_job(job_id: str, req: ScheduleJobCreate):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    sched = _get_scheduler()
    sched.remove_job(job_id)

    parts = req.cron.split()
    minute, hour, day, month, day_of_week = parts

    from scheduler.tasks import run_pipeline_job
    apj = sched.add_job(
        run_pipeline_job, trigger="cron",
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
        id=job_id, args=[job_id], replace_existing=True,
    )
    if not req.enabled:
        apj.pause()

    _jobs[job_id].update({
        "name": req.name, "cron": req.cron, "enabled": req.enabled,
        "days": req.days, "max_posts": req.max_posts,
        "top_celebs": req.top_celebs, "auto_publish": req.auto_publish,
    })

    return ScheduleJob(
        id=job_id, name=req.name, cron=req.cron, enabled=req.enabled,
        days=req.days, max_posts=req.max_posts, top_celebs=req.top_celebs,
        auto_publish=req.auto_publish,
        next_run=apj.next_run_time.isoformat() if apj.next_run_time else None,
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    sched = _get_scheduler()
    try:
        sched.remove_job(job_id)
    except Exception:
        pass
    del _jobs[job_id]
    return {"ok": True}


@router.post("/jobs/{job_id}/run")
async def trigger_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    sched = _get_scheduler()
    from scheduler.tasks import run_pipeline_job
    import asyncio
    asyncio.create_task(asyncio.to_thread(run_pipeline_job, job_id))
    return {"ok": True, "message": f"Job {job_id} triggered"}
