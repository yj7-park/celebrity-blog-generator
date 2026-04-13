"""Pydantic models for all API requests and responses."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Shared domain types ───────────────────────────────────────────────────────

class PostItem(BaseModel):
    title: str
    url: str
    date: str
    tag: str = ""


class OrderedBlock(BaseModel):
    type: str               # "text" | "image"
    content: Optional[str] = None
    url: Optional[str] = None


class ScrapedPostData(BaseModel):
    ordered_blocks: List[OrderedBlock] = []
    image_urls: List[str] = []
    paragraphs: List[str] = []
    links: List[Dict[str, str]] = []   # [{text, href}]
    post_url: str = ""
    title: str = ""


class CelebItem(BaseModel):
    celeb: str
    category: str
    product_name: str
    image_urls: List[str] = []
    candidate_image_urls: List[str] = []   # ±N neighbor images for cross-post matching
    processed_image_path: str = ""         # local path after image_processor (for blog writing)
    keywords: List[str] = []
    link_url: str = ""
    source_title: str = ""
    source_url: str = ""


class CoupangProduct(BaseModel):
    product_id: str = ""
    product_name: str
    product_image: str = ""
    product_url: str
    product_price: int = 0
    rating: float = 0.0
    review_count: int = 0
    affiliate_url: str = ""
    short_url: str = ""


# ── Pipeline endpoints ────────────────────────────────────────────────────────

class CollectRequest(BaseModel):
    days: int = 2


class CollectResponse(BaseModel):
    posts: List[PostItem]
    count: int


class AnalyzeRequest(BaseModel):
    posts: List[PostItem]
    openai_api_key: str = ""
    top_n: int = 5


class AnalyzeResponse(BaseModel):
    trending: List[str]
    post_count: int


class ScrapeRequest(BaseModel):
    posts: List[PostItem]
    celeb: str = ""
    max_posts: int = 10


class ScrapeResponse(BaseModel):
    scraped_count: int
    items: List[CelebItem]


class GenerateRequest(BaseModel):
    items: List[CelebItem]
    openai_api_key: str = ""
    image_placement: str = "두괄식"   # "두괄식" (image→text) | "미괄식" (text→image)


class GenerateResponse(BaseModel):
    celeb: str
    title: str = ""
    blog_post: str
    elements: List["BlogElement"] = []


# ── Coupang endpoints ─────────────────────────────────────────────────────────

class CoupangSearchRequest(BaseModel):
    keyword: str
    limit: int = 10


class CoupangSearchResponse(BaseModel):
    keyword: str
    products: List[CoupangProduct]


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    original_url: str
    short_url: str


# ── Naver blog writer ─────────────────────────────────────────────────────────

class BlogElement(BaseModel):
    type: str           # text | header | image | url | url_text | divider | callout
    content: Any        # str for text/header/url/url_text; file-path str for image; style name for divider
    style: Optional[str] = None  # callout style: quotation_postit|quotation_bubble|quotation_line|etc.


class NaverWriteRequest(BaseModel):
    title: str
    elements: List[BlogElement]
    tags: List[str] = []
    thumbnail_path: str = ""


class NaverWriteResponse(BaseModel):
    success: bool
    blog_url: str = ""
    error: str = ""


# ── Scheduler ─────────────────────────────────────────────────────────────────

class ScheduleJob(BaseModel):
    id: str
    name: str
    cron: str
    enabled: bool = True
    days: int = 2
    max_posts: int = 10
    top_celebs: int = 3
    auto_publish: bool = False
    last_run: Optional[str] = None
    next_run: Optional[str] = None


class ScheduleJobCreate(BaseModel):
    name: str
    cron: str
    enabled: bool = True
    days: int = 2
    max_posts: int = 10
    top_celebs: int = 3
    auto_publish: bool = False


# ── Blog source registry ──────────────────────────────────────────────────────

class BlogSource(BaseModel):
    id: str = ""
    name: str
    url: str
    image_mapping: str = "두괄식"    # "두괄식" (text→image) | "미괄식" (image→text)
    active: bool = True
    notes: str = ""
    created_at: str = ""
    last_scraped_at: Optional[str] = None


class BlogSourceCreate(BaseModel):
    name: str
    url: str
    image_mapping: str = "두괄식"
    active: bool = True
    notes: str = ""


class BlogSourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    image_mapping: Optional[str] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


# ── Image analysis ────────────────────────────────────────────────────────────

class WatermarkRegion(BaseModel):
    x: float               # 0-1 relative to image width
    y: float               # 0-1 relative to image height
    w: float               # 0-1 width fraction
    h: float               # 0-1 height fraction
    description: str = ""


class CandidateScore(BaseModel):
    url: str
    score: float                              # 0-1 relevance
    issues: List[str] = []                    # "watermark"|"mismatch"|"low_quality"|"cropped"
    explanation: str = ""
    watermark_region: Optional[WatermarkRegion] = None


class ItemImageAnalysis(BaseModel):
    item_index: int
    best_url: str
    best_score: float
    needs_review: bool
    candidates: List[CandidateScore] = []


class AnalyzeItemsRequest(BaseModel):
    items: List[CelebItem]
    openai_api_key: str = ""


class ProcessImageRequest(BaseModel):
    url: str
    watermark_region: Optional[WatermarkRegion] = None


# ── Settings ──────────────────────────────────────────────────────────────────

class AppSettings(BaseModel):
    openai_api_key: str = ""
    coupang_access_key: str = ""
    coupang_secret_key: str = ""
    coupang_domain: str = "https://api-gateway.coupang.com"
    naver_id: str = ""
    naver_pw: str = ""
    pipeline_days: int = 2
    pipeline_max_posts: int = 10
    pipeline_top_celebs: int = 5
    chrome_user_data_dir: str = "C:/Utilities/Blog/chrome-user-data"
    image_placement: str = "두괄식"   # "두괄식" (image→text) | "미괄식" (text→image)
