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
import asyncio, functools, json
from typing import AsyncGenerator, List
import anyio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel as _BaseModel

from services import cancel_token as _ct


async def _run(fn, *args, **kw):
    """Run a blocking function in a cancellable worker thread.

    Using ``anyio.to_thread.run_sync`` with ``cancellable=True`` means:
    - If the enclosing async task is cancelled (e.g. hot-reload / SIGTERM),
      the coroutine is released immediately — the server doesn't hang.
    - The worker thread itself continues briefly but will notice the cancel
      token and exit at its next checkpoint.
    """
    wrapped = functools.partial(fn, *args, **kw) if (args or kw) else fn
    return await anyio.to_thread.run_sync(wrapped, cancellable=True)

from models.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    AnalyzeItemsRequest,
    CelebItem,
    CollectRequest, CollectResponse,
    GenerateRequest, GenerateResponse,
    ProcessImageRequest,
    ScrapeRequest, ScrapeResponse,
    AppSettings,
)
from services.collector import collect_posts, scrape_multiple_posts
from services.image_analyzer import analyze_item as _analyze_item
from services.analyzer import get_trending_celebs
from services.extractor import extract_items_from_posts
from services.generator import generate_blog_elements
from services.coupang import search_products, shorten_url
from services.image_matcher import cross_match_items
from services.image_processor import process_image, process_items_images
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
    posts = await _run(collect_posts, req.days)
    return CollectResponse(posts=posts, count=len(posts))


@router.post("/analyze", response_model=AnalyzeResponse)
async def api_analyze(req: AnalyzeRequest):
    client = _get_client(req.openai_api_key)
    trending = await _run(get_trending_celebs, req.posts, client, req.top_n)
    return AnalyzeResponse(trending=trending, post_count=len(req.posts))


@router.post("/scrape", response_model=ScrapeResponse)
async def api_scrape(req: ScrapeRequest):
    settings = load_settings()
    client = _get_client(settings=settings)

    target_posts = req.posts
    if req.celeb:
        target_posts = _filter_posts_by_celeb(req.posts, req.celeb) or req.posts

    scraped_data, all_items = await _run(
        _scrape_and_extract_cached, target_posts, req.max_posts, client
    )

    if req.celeb:
        filtered = _filter_items_by_celeb(all_items, req.celeb)
        if filtered:
            all_items = filtered

    all_items = await _run(cross_match_items, all_items)
    return ScrapeResponse(scraped_count=len(scraped_data), items=all_items)


@router.post("/generate", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest):
    settings = load_settings()
    client = _get_client(req.openai_api_key)

    enriched = await _run(_enrich_with_coupang, req.items, settings)
    enriched = await _run(process_items_images, enriched)
    placement = req.image_placement or settings.image_placement or "두괄식"
    result   = await _run(generate_blog_elements, enriched, client, placement)
    celeb    = enriched[0].celeb if enriched else ""
    return GenerateResponse(
        celeb=celeb,
        title=result["title"],
        blog_post=result["blog_post"],
        elements=result["elements"],
    )


@router.post("/process-image")
async def api_process_image(req: ProcessImageRequest):
    """Download and process a single image URL. Returns the local file path.
    Optionally accepts watermark_region ({x,y,w,h} as 0-1 fractions) to
    remove a detected watermark before the standard pipeline.
    """
    try:
        wm_dict = req.watermark_region.model_dump() if req.watermark_region else None
        local_path = await _run(process_image, req.url, wm_dict)
    except Exception as e:
        import traceback, logging
        logging.error("process-image error: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"처리 오류: {e}")
    if not local_path:
        raise HTTPException(status_code=422, detail="이미지 처리 실패")
    return {"processed_path": local_path}


@router.post("/analyze-items")
async def api_analyze_items(req: AnalyzeItemsRequest):
    """SSE: analyze all items' images via GPT-4o vision.

    Streams per-item progress events, then a final 'done' event with
    full analysis results and review_count.
    """
    client = _get_client(req.openai_api_key)

    async def generate() -> AsyncGenerator[str, None]:
        _ct.pipeline.reset()
        try:
            total = len(req.items)
            yield _sse("progress", f"이미지 분석 시작 (총 {total}개 아이템)", 0)

            analyses = []
            for idx, item in enumerate(req.items):
                _ct.pipeline.check()
                yield _sse(
                    "progress",
                    f"[{idx+1}/{total}] {item.product_name} 분석 중...",
                    percent=int(idx / total * 100),
                )

                analysis = await _run(_analyze_item, idx, item, client)
                analyses.append(analysis)

                score_pct = f"{analysis.best_score:.0%}"
                review_flag = " ⚠️ 검토 필요" if analysis.needs_review else " ✅"
                yield _sse(
                    "progress",
                    f"[{idx+1}/{total}] {item.product_name} — {score_pct}{review_flag}",
                    percent=int((idx + 1) / total * 100),
                    data={"analysis": analysis.model_dump()},
                )

            review_count = sum(1 for a in analyses if a.needs_review)
            yield _sse(
                "done",
                f"분석 완료: {total}개 중 {review_count}개 검토 필요",
                100,
                data={
                    "analyses": [a.model_dump() for a in analyses],
                    "review_count": review_count,
                },
            )

        except InterruptedError:
            yield _sse("error", error="작업이 취소되었습니다.")
        except asyncio.CancelledError:
            _ct.pipeline.cancel()
            raise
        except Exception as e:
            yield _sse("error", error=str(e))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/cancel")
async def cancel_pipeline():
    """Immediately signal all running pipeline threads to stop."""
    _ct.pipeline.cancel()
    return {"status": "cancelled"}


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
        # Look up per-source image_mapping setting
        source = _db.get_source_for_post_url(post.url)
        src_image_mapping = source["image_mapping"] if source else "두괄식"
        if source:
            try:
                _db.touch_source_scraped(source["id"])
            except Exception:
                pass

        from services.extractor import extract_from_post as _extract_one
        try:
            post_items = _extract_one(scraped, client, src_image_mapping)
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
        _ct.pipeline.reset()
        try:
            client = OpenAI(api_key=api_key)

            # ── Phase 1: Collect RSS ──────────────────────────────────────────
            yield _sse("progress", "RSS 수집 중...", 5)
            posts_result = await _run(collect_posts, days)
            _ct.pipeline.check()
            if not posts_result:
                yield _sse("error", error="게시글을 찾을 수 없습니다.")
                return

            yield _sse("progress", f"RSS 수집 완료: {len(posts_result)}개", 18,
                       data={"posts": [p.model_dump() for p in posts_result[:20]]})

            # ── Phase 2: Trending analysis ────────────────────────────────────
            yield _sse("progress", "트렌딩 연예인 분석 중...", 22)
            _ct.pipeline.check()
            trending = await _run(get_trending_celebs, posts_result, client, top_celebs)
            _ct.pipeline.check()
            if not trending:
                yield _sse("error", error="연예인을 찾을 수 없습니다.")
                return

            celeb = trending[0]
            yield _sse("progress", f"분석 완료: {', '.join(trending)}", 38,
                       data={"trending": trending, "selected": celeb})

            # ── Phase 3: Scrape + Extract (cache-aware) ───────────────────────
            yield _sse("progress", f"{celeb} 포스트 스크랩·추출 중 (캐시 확인)...", 42)
            target_posts = _filter_posts_by_celeb(posts_result, celeb) or posts_result

            _ct.pipeline.check()
            scraped, all_items = await _run(
                _scrape_and_extract_cached,
                target_posts, min(max_posts, len(target_posts)), client
            )

            celeb_items_filtered = _filter_items_by_celeb(all_items, celeb)
            final_items = celeb_items_filtered if celeb_items_filtered else all_items

            yield _sse("progress", f"스크랩 {len(scraped)}개 완료 (아이템 {len(final_items)}개)", 62)

            # ── Phase 4: Image matching + processing ──────────────────────────
            yield _sse("progress", "이미지 매칭 중...", 66)
            _ct.pipeline.check()
            final_items = await _run(cross_match_items, final_items)

            yield _sse("progress", "이미지 가공 중...", 70)
            _ct.pipeline.check()
            final_items = await _run(process_items_images, final_items)

            yield _sse("progress", f"아이템 추출 완료: {len(final_items)}개", 72,
                       data={"items": [it.model_dump() for it in final_items]})

            # ── Phase 5: Coupang affiliate search ─────────────────────────────
            yield _sse("progress", "쿠팡 어필리에이션 URL 생성 중...", 76)
            _ct.pipeline.check()
            enriched_items = await _run(_enrich_with_coupang, final_items, settings)
            linked_count = sum(1 for it in enriched_items if it.link_url)
            yield _sse("progress", f"쿠팡 링크 완료: {linked_count}/{len(enriched_items)}개", 82,
                       data={"items": [it.model_dump() for it in enriched_items]})

            # Save to celeb_items store (upsert)
            try:
                await _run(_db.save_celeb_items, [it.model_dump() for it in enriched_items])
            except Exception:
                pass

            # ── Phase 6: Generate blog post ───────────────────────────────────
            yield _sse("progress", "블로그 포스트 생성 중...", 86)
            _ct.pipeline.check()
            placement = settings.image_placement or "두괄식"
            result = await _run(generate_blog_elements, enriched_items, client, placement)

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
                await _run(
                    _db.save_run,
                    celeb,
                    [it.model_dump() for it in enriched_items],
                    result["blog_post"],
                    result["title"],
                    [el.model_dump() for el in result["elements"]],
                )
            except Exception:
                pass

        except InterruptedError:
            # Manual cancel via /cancel endpoint — inform the client
            yield _sse("error", error="작업이 취소되었습니다.")
        except asyncio.CancelledError:
            # Server is shutting down / hot-reload — release immediately
            _ct.pipeline.cancel()
            raise
        except Exception as e:
            yield _sse("error", error=str(e))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
