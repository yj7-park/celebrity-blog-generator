"""
Pipeline router: collect → analyze → scrape → extract → generate
Supports both REST and Server-Sent Events (SSE) streaming.
"""
from __future__ import annotations
import asyncio, json
from typing import AsyncGenerator, List
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import OpenAI

from models.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    CollectRequest, CollectResponse,
    GenerateRequest, GenerateResponse,
    ScrapeRequest, ScrapeResponse,
    AppSettings,
)
from services.collector import collect_posts, scrape_multiple_posts
from services.analyzer import get_trending_celebs
from services.extractor import extract_items_from_posts
from services.generator import generate_blog_post
from services.settings_service import load_settings

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _get_client(api_key: str = "", settings: AppSettings = None) -> OpenAI:
    key = api_key or (settings.openai_api_key if settings else "")
    if not key:
        key = load_settings().openai_api_key
    return OpenAI(api_key=key)


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.post("/collect", response_model=CollectResponse)
async def api_collect(req: CollectRequest):
    posts = await asyncio.to_thread(collect_posts, req.days)
    return CollectResponse(posts=posts, count=len(posts))


@router.post("/analyze", response_model=AnalyzeResponse)
async def api_analyze(req: AnalyzeRequest):
    client = _get_client(req.openai_api_key)
    trending = await asyncio.to_thread(get_trending_celebs, req.posts, client, req.top_n)
    return AnalyzeResponse(trending=trending, post_count=len(req.posts))


@router.post("/scrape", response_model=ScrapeResponse)
async def api_scrape(req: ScrapeRequest):
    settings = load_settings()
    client = _get_client(settings=settings)

    # Filter posts by celeb name if provided
    target_posts = req.posts
    if req.celeb:
        filtered = [p for p in req.posts if req.celeb in p.title]
        if len(filtered) >= 3:
            target_posts = filtered

    scraped = await asyncio.to_thread(
        scrape_multiple_posts, target_posts, req.max_posts
    )
    items = await asyncio.to_thread(extract_items_from_posts, scraped, client)

    if req.celeb:
        filtered_items = [it for it in items if req.celeb in it.celeb or it.celeb in req.celeb]
        if filtered_items:
            items = filtered_items

    return ScrapeResponse(scraped_count=len(scraped), items=items)


@router.post("/generate", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest):
    client = _get_client(req.openai_api_key)
    post = await asyncio.to_thread(generate_blog_post, req.items, client)
    celeb = req.items[0].celeb if req.items else ""
    return GenerateResponse(celeb=celeb, blog_post=post)


# ── SSE full pipeline ─────────────────────────────────────────────────────────

def _sse(event_type: str, step: str = "", percent: int = 0, data=None, error: str = "") -> str:
    payload = json.dumps({
        "type": event_type, "step": step,
        "percent": percent, "data": data, "error": error,
    }, ensure_ascii=False)
    return f"data: {payload}\n\n"


@router.get("/run")
async def run_pipeline(
    days: int = 2,
    max_posts: int = 10,
    top_celebs: int = 3,
    openai_api_key: str = "",
    auto_publish: bool = False,
):
    settings = load_settings()
    api_key = openai_api_key or settings.openai_api_key

    async def generate() -> AsyncGenerator[str, None]:
        try:
            client = OpenAI(api_key=api_key)

            # ── Phase 1: Collect RSS ──────────────────────────────────────────
            yield _sse("progress", "RSS 수집 중...", 5)
            posts_result: list = []

            def do_collect():
                def prog(done, total):
                    pass  # We'll emit a single done event
                return collect_posts(days, prog)

            posts_result = await asyncio.to_thread(do_collect)
            if not posts_result:
                yield _sse("error", error="게시글을 찾을 수 없습니다.")
                return

            yield _sse("progress", f"RSS 수집 완료: {len(posts_result)}개", 22,
                       data={"posts": [p.model_dump() for p in posts_result[:20]]})

            # ── Phase 2: Trending analysis ────────────────────────────────────
            yield _sse("progress", "트렌딩 연예인 분석 중...", 25)
            trending = await asyncio.to_thread(
                get_trending_celebs, posts_result, client, top_celebs
            )
            if not trending:
                yield _sse("error", error="연예인을 찾을 수 없습니다.")
                return

            celeb = trending[0]
            yield _sse("progress", f"분석 완료: {', '.join(trending)}", 42,
                       data={"trending": trending, "selected": celeb})

            # ── Phase 3: Scrape + Extract ─────────────────────────────────────
            yield _sse("progress", f"{celeb} 포스트 스크랩 중...", 45)
            target_posts = [p for p in posts_result if celeb in p.title] or posts_result
            scraped = await asyncio.to_thread(
                scrape_multiple_posts, target_posts, min(max_posts, len(target_posts))
            )
            yield _sse("progress", f"스크랩 완료: {len(scraped)}개", 65)

            yield _sse("progress", "LLM 아이템 추출 중...", 68)
            all_items = await asyncio.to_thread(extract_items_from_posts, scraped, client)
            celeb_items = [it for it in all_items if celeb in it.celeb or it.celeb in celeb]
            final_items = celeb_items if celeb_items else all_items

            yield _sse("progress", f"아이템 추출 완료: {len(final_items)}개", 80,
                       data={"items": [it.model_dump() for it in final_items]})

            # ── Phase 4: Generate blog post ───────────────────────────────────
            yield _sse("progress", "블로그 포스트 생성 중...", 85)
            blog_post = await asyncio.to_thread(generate_blog_post, final_items, client)

            yield _sse("done", "완료!", 100, data={
                "celeb": celeb,
                "blog_post": blog_post,
                "items": [it.model_dump() for it in final_items],
                "trending": trending,
                "posts_count": len(posts_result),
            })

        except Exception as e:
            yield _sse("error", error=str(e))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
