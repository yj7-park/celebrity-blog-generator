"""Coupang affiliate API endpoints."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from models.schemas import CoupangSearchRequest, CoupangSearchResponse, ShortenRequest, ShortenResponse
from services.coupang import search_products, shorten_url, get_affiliate_landing_url
from services.settings_service import load_settings

router = APIRouter(prefix="/api/coupang", tags=["coupang"])


@router.post("/search", response_model=CoupangSearchResponse)
async def api_coupang_search(req: CoupangSearchRequest):
    settings = load_settings()
    if not settings.coupang_access_key:
        raise HTTPException(status_code=400, detail="Coupang API 키가 설정되지 않았습니다.")
    import asyncio
    products = await asyncio.to_thread(search_products, req.keyword, settings, req.limit)
    return CoupangSearchResponse(keyword=req.keyword, products=products)


@router.post("/shorten", response_model=ShortenResponse)
async def api_shorten(req: ShortenRequest):
    import asyncio
    short = await asyncio.to_thread(shorten_url, req.url)
    return ShortenResponse(original_url=req.url, short_url=short)


@router.get("/affiliate")
async def api_affiliate_url(product_url: str):
    settings = load_settings()
    import asyncio
    url = await asyncio.to_thread(get_affiliate_landing_url, product_url, settings)
    short = await asyncio.to_thread(shorten_url, url)
    return {"original_url": product_url, "affiliate_url": url, "short_url": short}
