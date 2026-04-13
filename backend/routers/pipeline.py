"""
Pipeline router: collect → analyze → scrape → extract → coupang → generate
Supports both REST and Server-Sent Events (SSE) streaming.
"""
from __future__ import annotations
import asyncio, json
from typing import AsyncGenerator, List
from fastapi import APIRouter
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
from services.generator import generate_blog_elements
from services.coupang import search_products, shorten_url
from services.image_matcher import cross_match_items
from services.image_processor import process_items_images
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
        target_posts = _filter_posts_by_celeb(req.posts, req.celeb) or req.posts

    scraped = await asyncio.to_thread(
        scrape_multiple_posts, target_posts, req.max_posts
    )
    items = await asyncio.to_thread(extract_items_from_posts, scraped, client)

    if req.celeb:
        filtered_items = _filter_items_by_celeb(items, req.celeb)
        if filtered_items:
            items = filtered_items

    # Cross-post image matching: pick most consistent image per item
    items = await asyncio.to_thread(cross_match_items, items)

    return ScrapeResponse(scraped_count=len(scraped), items=items)


@router.post("/generate", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest):
    settings = load_settings()
    client = _get_client(req.openai_api_key)

    # Enrich items with Coupang affiliate URLs if not already set
    enriched = await asyncio.to_thread(_enrich_with_coupang, req.items, settings)

    result = await asyncio.to_thread(generate_blog_elements, enriched, client)
    celeb = enriched[0].celeb if enriched else ""
    return GenerateResponse(
        celeb=celeb,
        title=result["title"],
        blog_post=result["blog_post"],
        elements=result["elements"],
    )


# ── Celebrity filtering helpers ───────────────────────────────────────────────

def _celeb_tokens(name: str) -> list[str]:
    """Split a celeb name into searchable tokens (handles spaces, English aliases)."""
    tokens = [name.strip()]
    # Add each word as a separate token (e.g. "한소희" stays whole, but "IU 아이유" → ["IU", "아이유"])
    parts = name.strip().split()
    if len(parts) > 1:
        tokens.extend(parts)
    # Lowercase variant for English names
    tokens.extend([t.lower() for t in tokens if t.isascii()])
    return list(dict.fromkeys(t for t in tokens if t))  # deduplicate, preserve order


def _filter_posts_by_celeb(posts, celeb: str):
    """
    Multi-strategy post filtering:
    1. Exact name match in title
    2. Any token match in title
    Falls back to all posts if fewer than 3 posts matched.
    """
    tokens = _celeb_tokens(celeb)
    # Strategy 1: full name in title
    exact = [p for p in posts if celeb in p.title]
    if len(exact) >= 3:
        return exact
    # Strategy 2: any token match
    token_matched = [
        p for p in posts
        if any(tok in p.title for tok in tokens)
    ]
    if len(token_matched) >= 3:
        return token_matched
    # Strategy 3: return all (let LLM extractor handle it)
    return posts


def _filter_items_by_celeb(items, celeb: str):
    """Filter extracted CelebItems by celeb name with token matching."""
    tokens = _celeb_tokens(celeb)
    matched = [
        it for it in items
        if any(tok in it.celeb or it.celeb in tok for tok in tokens)
    ]
    return matched


# ── Coupang enrichment helper ─────────────────────────────────────────────────

def _enrich_with_coupang(items, settings: AppSettings):
    """Search Coupang for each item by product_name and attach affiliate URL."""
    if not settings.coupang_access_key or not settings.coupang_secret_key:
        return items

    enriched = []
    for item in items:
        try:
            products = search_products(item.product_name, settings, limit=1)
            if products:
                affiliate = products[0].affiliate_url or products[0].product_url
                short = shorten_url(affiliate)
                item = item.model_copy(update={"link_url": short or affiliate})
        except Exception:
            pass
        enriched.append(item)
    return enriched


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

            def do_collect():
                return collect_posts(days)

            posts_result = await asyncio.to_thread(do_collect)
            if not posts_result:
                yield _sse("error", error="게시글을 찾을 수 없습니다.")
                return

            yield _sse("progress", f"RSS 수집 완료: {len(posts_result)}개", 18,
                       data={"posts": [p.model_dump() for p in posts_result[:20]]})

            # ── Phase 2: Trending analysis ────────────────────────────────────
            yield _sse("progress", "트렌딩 연예인 분석 중...", 22)
            trending = await asyncio.to_thread(
                get_trending_celebs, posts_result, client, top_celebs
            )
            if not trending:
                yield _sse("error", error="연예인을 찾을 수 없습니다.")
                return

            celeb = trending[0]
            yield _sse("progress", f"분석 완료: {', '.join(trending)}", 38,
                       data={"trending": trending, "selected": celeb})

            # ── Phase 3: Scrape + Extract ─────────────────────────────────────
            yield _sse("progress", f"{celeb} 포스트 스크랩 중...", 42)
            target_posts = _filter_posts_by_celeb(posts_result, celeb) or posts_result
            scraped = await asyncio.to_thread(
                scrape_multiple_posts, target_posts, min(max_posts, len(target_posts))
            )
            yield _sse("progress", f"스크랩 완료: {len(scraped)}개", 58)

            yield _sse("progress", "LLM 아이템 추출 중...", 62)
            all_items = await asyncio.to_thread(extract_items_from_posts, scraped, client)
            celeb_items = _filter_items_by_celeb(all_items, celeb)
            final_items = celeb_items if celeb_items else all_items

            # Cross-post image matching
            yield _sse("progress", "이미지 매칭 중...", 66)
            final_items = await asyncio.to_thread(cross_match_items, final_items)

            # Image processing: edge-crop watermarks + add brand label
            yield _sse("progress", "이미지 가공 중...", 70)
            final_items = await asyncio.to_thread(process_items_images, final_items)

            yield _sse("progress", f"아이템 추출 완료: {len(final_items)}개", 72,
                       data={"items": [it.model_dump() for it in final_items]})

            # ── Phase 4: Coupang affiliate search ─────────────────────────────
            yield _sse("progress", "쿠팡 어필리에이션 URL 생성 중...", 76)
            enriched_items = await asyncio.to_thread(
                _enrich_with_coupang, final_items, settings
            )
            linked_count = sum(1 for it in enriched_items if it.link_url)
            yield _sse("progress", f"쿠팡 링크 완료: {linked_count}/{len(enriched_items)}개", 82,
                       data={"items": [it.model_dump() for it in enriched_items]})

            # ── Phase 5: Generate blog post ───────────────────────────────────
            yield _sse("progress", "블로그 포스트 생성 중...", 86)
            result = await asyncio.to_thread(generate_blog_elements, enriched_items, client)

            yield _sse("done", "완료!", 100, data={
                "celeb": celeb,
                "title": result["title"],
                "blog_post": result["blog_post"],
                "elements": [el.model_dump() for el in result["elements"]],
                "items": [it.model_dump() for it in enriched_items],
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
