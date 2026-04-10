"""Naver blog writer endpoints (Selenium)."""
from __future__ import annotations
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import NaverWriteRequest, NaverWriteResponse
from services.naver_writer import NaverBlogWriter
from services.settings_service import load_settings

router = APIRouter(prefix="/api/naver", tags=["naver"])

# Track current writer status
_writer_status: dict = {"running": False, "last_url": "", "last_error": ""}


@router.get("/status")
async def get_status():
    return _writer_status


@router.post("/write", response_model=NaverWriteResponse)
async def write_blog_post(req: NaverWriteRequest):
    settings = load_settings()
    if not settings.naver_id or not settings.naver_pw:
        raise HTTPException(status_code=400, detail="Naver ID/PW가 설정되지 않았습니다.")

    if _writer_status["running"]:
        raise HTTPException(status_code=409, detail="이미 블로그 작성이 진행 중입니다.")

    _writer_status["running"] = True
    _writer_status["last_error"] = ""

    try:
        writer = NaverBlogWriter(
            naver_id=settings.naver_id,
            naver_pw=settings.naver_pw,
            chrome_user_data_dir=settings.chrome_user_data_dir,
        )

        elements = [el.model_dump() for el in req.elements]
        blog_url = await asyncio.to_thread(
            writer.write,
            req.title,
            elements,
            req.thumbnail_path,
        )
        _writer_status["last_url"] = blog_url
        return NaverWriteResponse(success=True, blog_url=blog_url)

    except Exception as e:
        _writer_status["last_error"] = str(e)
        return NaverWriteResponse(success=False, error=str(e))

    finally:
        _writer_status["running"] = False
