"""
Pipeline router: collect → analyze → scrape → extract → coupang → generate
Supports both REST and Server-Sent Events (SSE) streaming.

Caching strategy
----------------
scraped_posts   : cache per (post_url, content_hash)  — skip re-scraping
extracted_items : cache per (post_url, content_hash)  — skip LLM extraction (most expensive)
celeb_items     : saved after Coupang enrichment (final state, queryable)
pipeline_runs   : saved after blog generation (history)
"""
from __future__ import annotations
import asyncio, json
from typing import AsyncGenerator, List
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import OpenAI

from models.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    CelebItem,
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
import db as _db

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

    target_posts = req.posts
    if req.celeb:
        target_posts = _filter_posts_by_celeb(req.posts, req.celeb) or req.posts

    scraped_data, all_items = await asyncio.to_thread(
        _scrape_and_extract_cached, target_posts, req.max_posts, client
    )

    if req.celeb:
        filtered = _filter_items_by_celeb(all_items, req.celeb)
        if filtered:
            all_items = filtered

    all_items = await asyncio.to_thread(cross_match_items, all_items)
    return ScrapeResponse(scraped_count=len(scraped_data), items=all_items)


@router.post("/generate", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest):
    settings = load_settings()
    client = _get_client(req.openai_api_key)

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
    tokens = [name.strip()]
    parts = name.strip().split()
    if len(parts) > 1:
        tokens.extend(parts)
    tokens.extend([t.lower() for t in tokens if t.isascii()])
    return list(dict.fromkeys(t for t in tokens if t))


def _filter_posts_by_celeb(posts, celeb: str):
    tokens = _celeb_tokens(celeb)
    exact = [p for p in posts if celeb in p.title]
    if len(exact) >= 3:
        return exact
    token_matched = [p for p in posts if any(tok in p.title for tok in tokens)]
    if len(token_matched) >= 3:
        return token_matched
    return posts


def _filter_items_by_celeb(items, celeb: str):
    tokens = _celeb_tokens(celeb)
    matched = [
        it for it in items
        if any(tok in it.celeb or it.celeb in tok for tok in tokens)
    ]
    return matched


# ── Coupang enrichment ────────────────────────────────────────────────────────

def _enrich_with_coupang(items, settings: AppSettings):
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


# ── Cache-aware scrape + extract ──────────────────────────────────────────────

def _scrape_and_extract_cached(target_posts, max_posts: int, client) -> tuple:
    """
    Scrape posts and extract items, using DB cache to skip unchanged content.

    Returns (scraped_list, all_items).
    """
    from services.collector import scrape_post as _scrape_one

    scraped_list = []
    all_items: List[CelebItem] = []
    seen_urls: set[str] = set()

    for post in target_posts[:max_posts]:
        if post.url in seen_urls:
            continue
        seen_urls.add(post.url)

        try:
            scraped = _scrape_one(post)
        except Exception:
            continue
        if not scraped:
            continue

        scraped_list.append(scraped)

        # Compute content hash from scraped data
        chash = _db.content_hash(scraped.model_dump())

        # Save scraping cache (upsert — harmless if already exists)
        try:
            _db.save_scraped_post(post.url, scraped.title or post.title,
                                   chash, scraped.model_dump())
        except Exception:
            pass

        # Check extraction cache
        cached_items = _db.get_extracted_items(post.url, chash)
        if cached_items is not None:
            # Re-hydrate Pydantic models from cached dicts
            for d in cached_items:
                try:
                    all_items.append(CelebItem(**d))
                except Exception:
                    pass
            continue

        # Cache miss — run LLM extraction
        from services.extractor import extract_from_post as _extract_one
        try:
            post_items = _extract_one(scraped, client)
        except Exception:
            post_items = []

        # Save extraction cache
        try:
            _db.save_extracted_items(
                post.url, chash,
                [it.model_dump() for it in post_items],
            )
        except Exception:
            pass

        all_items.extend(post_items)

    return scraped_list, all_items


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(event_type: str, step: str = "", percent: int = 0,
         data=None, error: str = "", cached: bool = False) -> str:
    payload = json.dumps({
        "type": event_type, "step": step, "percent": percent,
        "data": data, "error": error, "cached": cached,
    }, ensure_ascii=False)
    return f"data: {payload}\n\n"


# ── SSE full pipeline ─────────────────────────────────────────────────────────

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
            posts_result = await asyncio.to_thread(collect_posts, days)
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

            # ── Phase 3: Scrape + Extract (cache-aware) ───────────────────────
            yield _sse("progress", f"{celeb} 포스트 스크랩·추출 중 (캐시 확인)...", 42)
            target_posts = _filter_posts_by_celeb(posts_result, celeb) or posts_result

            scraped, all_items = await asyncio.to_thread(
                _scrape_and_extract_cached,
                target_posts, min(max_posts, len(target_posts)), client
            )

            celeb_items_filtered = _filter_items_by_celeb(all_items, celeb)
            final_items = celeb_items_filtered if celeb_items_filtered else all_items

            yield _sse("progress", f"스크랩 {len(scraped)}개 완료 (아이템 {len(final_items)}개)", 62)

            # ── Phase 4: Image matching + processing ──────────────────────────
            yield _sse("progress", "이미지 매칭 중...", 66)
            final_items = await asyncio.to_thread(cross_match_items, final_items)

            yield _sse("progress", "이미지 가공 중...", 70)
            final_items = await asyncio.to_thread(process_items_images, final_items)

            yield _sse("progress", f"아이템 추출 완료: {len(final_items)}개", 72,
                       data={"items": [it.model_dump() for it in final_items]})

            # ── Phase 5: Coupang affiliate search ─────────────────────────────
            yield _sse("progress", "쿠팡 어필리에이션 URL 생성 중...", 76)
            enriched_items = await asyncio.to_thread(
                _enrich_with_coupang, final_items, settings
            )
            linked_count = sum(1 for it in enriched_items if it.link_url)
            yield _sse("progress", f"쿠팡 링크 완료: {linked_count}/{len(enriched_items)}개", 82,
                       data={"items": [it.model_dump() for it in enriched_items]})

            # Save to celeb_items store (upsert — always overwrite with freshest data)
            try:
                await asyncio.to_thread(
                    _db.save_celeb_items,
                    [it.model_dump() for it in enriched_items],
                )
            except Exception:
                pass

            # ── Phase 6: Generate blog post ───────────────────────────────────
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

            # Save pipeline run (non-blocking)
            try:
                await asyncio.to_thread(
                    _db.save_run,
                    celeb,
                    [it.model_dump() for it in enriched_items],
                    result["blog_post"],
                    result["title"],
                    [el.model_dump() for el in result["elements"]],
                )
            except Exception:
                pass

        except Exception as e:
            yield _sse("error", error=str(e))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
