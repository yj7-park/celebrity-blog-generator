import json
import os
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openai import OpenAI

from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CollectRequest,
    CollectResponse,
    GenerateRequest,
    GenerateResponse,
    ItemsRequest,
    ItemsResponse,
    PostItem,
)
from services.analyzer import get_trending_celebs
from services.collector import collect_posts, get_items_for_celeb
from services.generator import generate_blog_post

router = APIRouter(prefix="/api", tags=["blog"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/collect", response_model=CollectResponse)
def collect(req: CollectRequest):
    try:
        posts = collect_posts(days=req.days)
        return CollectResponse(posts=[PostItem(**p) for p in posts], count=len(posts))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        client = OpenAI(api_key=req.openai_api_key)
        posts_data = [p.model_dump() for p in req.posts]
        trending = get_trending_celebs(posts_data, client, top_n=req.top_n)
        return AnalyzeResponse(trending=trending, post_count=len(req.posts))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items", response_model=ItemsResponse)
def items(req: ItemsRequest):
    try:
        posts_data = [p.model_dump() for p in req.posts]
        items_dict, snippets = get_items_for_celeb(posts_data, req.celeb)
        return ItemsResponse(celeb=req.celeb, items=items_dict, content_snippets=snippets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        client = OpenAI(api_key=req.openai_api_key)
        post = generate_blog_post(req.celeb, req.items, req.content_snippets, client)
        return GenerateResponse(celeb=req.celeb, blog_post=post)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline")
async def pipeline(
    days: int = Query(default=2, ge=1, le=7),
    openai_api_key: str = Query(default=""),
):
    """SSE endpoint — streams progress events for the full pipeline."""
    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenAI API key required")

    async def event_stream() -> AsyncGenerator[str, None]:
        def _sse(payload: dict) -> str:
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            client = OpenAI(api_key=api_key)

            # Step 1 – collect RSS posts
            yield _sse({"type": "progress", "step": "블로그 RSS 수집 중...", "percent": 10})
            posts = collect_posts(days=days)
            yield _sse({"type": "posts", "data": {"count": len(posts), "titles": [p["title"] for p in posts[:10]]}})
            yield _sse({"type": "progress", "step": f"{len(posts)}개 게시글 수집 완료", "percent": 30})

            if not posts:
                yield _sse({"type": "error", "message": "수집된 게시글이 없습니다."})
                return

            # Step 2 – extract trending celebrities
            yield _sse({"type": "progress", "step": "트렌딩 연예인 분석 중...", "percent": 40})
            trending = get_trending_celebs(posts, client, top_n=3)
            yield _sse({"type": "trending", "data": {"celebs": trending}})
            yield _sse({"type": "progress", "step": f'트렌딩 연예인: {", ".join(trending)}', "percent": 60})

            if not trending:
                yield _sse({"type": "error", "message": "연예인을 찾을 수 없습니다."})
                return

            celeb = trending[0]

            # Step 3 – scrape items for top celebrity
            yield _sse({"type": "progress", "step": f"{celeb} 아이템 수집 중...", "percent": 70})
            items_dict, snippets = get_items_for_celeb(posts, celeb)
            yield _sse({"type": "items", "data": {"items": items_dict}})
            yield _sse({"type": "progress", "step": f"{len(items_dict)}개 아이템 수집 완료", "percent": 85})

            # Step 4 – generate blog post
            yield _sse({"type": "progress", "step": "블로그 게시글 생성 중...", "percent": 90})
            blog_post = generate_blog_post(celeb, items_dict, snippets, client)
            yield _sse({"type": "blog_post", "data": {"celeb": celeb, "post": blog_post}})
            yield _sse({"type": "progress", "step": "완료!", "percent": 100})
            yield _sse({"type": "done"})

        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
