"""Naver blog writer endpoints (Selenium)."""
from __future__ import annotations
import asyncio
import anyio
from fastapi import APIRouter, HTTPException
from models.schemas import NaverWriteRequest, NaverWriteResponse
from services.naver_writer import NaverBlogWriter
from services.settings_service import load_settings
from services import cancel_token as _ct

router = APIRouter(prefix="/api/naver", tags=["naver"])

# Track current writer status (read by the frontend via polling)
_writer_status: dict = {
    "running": False,
    "phase": "idle",       # idle | logging_in | writing | verification_needed | done | error
    "message": "",
    "last_url": "",
    "last_error": "",
}


@router.get("/status")
async def get_status():
    return _writer_status


@router.post("/cancel")
async def cancel_naver():
    """Signal the Selenium writer to stop at the next element boundary."""
    _ct.naver.cancel()
    return {"status": "cancelled"}


@router.post("/write", response_model=NaverWriteResponse)
async def write_blog_post(req: NaverWriteRequest):
    settings = load_settings()
    if not settings.naver_id or not settings.naver_pw:
        raise HTTPException(status_code=400, detail="Naver ID/PW가 설정되지 않았습니다.")

    if _writer_status["running"]:
        raise HTTPException(status_code=409, detail="이미 블로그 작성이 진행 중입니다.")

    _ct.naver.reset()
    _writer_status["running"]    = True
    _writer_status["phase"]      = "logging_in"
    _writer_status["message"]    = "Naver 로그인 중..."
    _writer_status["last_error"] = ""
    _writer_status["last_url"]   = ""

    def _status_cb(phase: str, message: str):
        _writer_status["phase"]   = phase
        _writer_status["message"] = message

    def _run_writer():
        writer = NaverBlogWriter(
            naver_id=settings.naver_id,
            naver_pw=settings.naver_pw,
            chrome_user_data_dir=settings.chrome_user_data_dir,
        )
        elements = [el.model_dump() for el in req.elements]
        _writer_status["phase"]   = "writing"
        _writer_status["message"] = "블로그 작성 중..."
        return writer.write(req.title, elements, req.thumbnail_path, _status_cb, req.tags)

    try:
        # cancellable=True: on hot-reload / SIGTERM the coroutine is released
        # immediately; the thread finishes its current element then stops via
        # the cancel token checked inside _delay() and the element loop.
        blog_url = await anyio.to_thread.run_sync(_run_writer, cancellable=True)
        _writer_status["last_url"] = blog_url
        _writer_status["phase"]    = "done"
        _writer_status["message"]  = "발행 완료"
        return NaverWriteResponse(success=True, blog_url=blog_url)

    except InterruptedError:
        _writer_status["last_error"] = "작업이 취소되었습니다."
        _writer_status["phase"]      = "error"
        _writer_status["message"]    = "작업이 취소되었습니다."
        return NaverWriteResponse(success=False, error="작업이 취소되었습니다.")

    except asyncio.CancelledError:
        # Server shutting down — set the cancel token so the thread stops
        _ct.naver.cancel()
        raise

    except Exception as e:
        _writer_status["last_error"] = str(e)
        _writer_status["phase"]      = "error"
        _writer_status["message"]    = str(e)
        return NaverWriteResponse(success=False, error=str(e))

    finally:
        _writer_status["running"] = False
