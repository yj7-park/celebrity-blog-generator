import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routers.pipeline import router as pipeline_router
from routers.coupang import router as coupang_router
from routers.naver import router as naver_router
from routers.scheduler import router as scheduler_router
from routers.settings import router as settings_router
from routers.proxy import router as proxy_router
from routers.db import router as db_router
from routers.sources import router as sources_router
import db as _db
from services import cancel_token as _ct

# Global APScheduler instance (imported by scheduler router)
scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _db.init_db()
    scheduler.start()
    yield
    # Signal all blocking threads to exit promptly so hot-reload is fast
    _ct.pipeline.cancel()
    _ct.naver.cancel()
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="셀럽 아이템 블로그 자동화 시스템",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)
app.include_router(coupang_router)
app.include_router(naver_router)
app.include_router(scheduler_router)
app.include_router(settings_router)
app.include_router(proxy_router)
app.include_router(db_router)
app.include_router(sources_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# Serve built frontend (ws2/frontend/dist → copied to backend/static)
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    _ASSETS = os.path.join(_STATIC_DIR, "assets")
    if os.path.isdir(_ASSETS):
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
