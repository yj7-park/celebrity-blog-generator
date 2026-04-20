"""
Vision-model-based image analysis for CelebItem images.

For each item:
1. Score image relevance against item context (celeb, product, keywords) using GPT-4o
2. Detect watermarks — position + type
3. Detect other issues: mismatch, low quality, cropped subject
4. Rank all candidate images by score

Returns ItemImageAnalysis with best_url, best_score, needs_review flag, and
full candidate list for human-in-the-loop review.
"""
from __future__ import annotations

import base64
import io
import json
import warnings
from typing import Optional, List

import requests
from PIL import Image

from models.schemas import (
    CandidateScore, ItemImageAnalysis, WatermarkRegion, CelebItem
)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_CANDIDATES_PER_ITEM = 6      # GPT-4o vision cost cap
NEEDS_REVIEW_THRESHOLD  = 0.65   # below this → needs human review
DOWNLOAD_TIMEOUT        = 8


# ── Image download + encode ───────────────────────────────────────────────────

def _fetch_base64(url: str) -> Optional[tuple[str, str]]:
    """Download image → (base64_str, mime_type). Returns None on failure."""
    try:
        warnings.filterwarnings("ignore")
        resp = requests.get(
            url, timeout=DOWNLOAD_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
            verify=False,
        )
        resp.raise_for_status()
        raw = resp.content

        # Detect format from content
        try:
            img = Image.open(io.BytesIO(raw))
            fmt = (img.format or "JPEG").upper()
        except Exception:
            fmt = "JPEG"

        mime_map = {"JPEG": "image/jpeg", "PNG": "image/png",
                    "GIF": "image/gif", "WEBP": "image/webp"}
        mime = mime_map.get(fmt, "image/jpeg")
        return base64.b64encode(raw).decode(), mime
    except Exception:
        return None


# ── Vision prompt ─────────────────────────────────────────────────────────────

def _make_prompt(item: CelebItem) -> str:
    kw_str = ", ".join(item.keywords[:6]) or "없음"
    return f"""이미지가 다음 아이템 정보와 얼마나 일치하는지 분석하세요.

아이템 정보:
- 카테고리: {item.category}
- 제품명: {item.product_name}
- 키워드: {kw_str}

다음 JSON으로만 응답하세요 (마크다운 없이):
{{
  "score": <0.0~1.0>,
  "issues": [<"watermark"|"mismatch"|"low_quality"|"cropped" 해당 항목들>],
  "explanation": "<한 문장 한국어 설명>",
  "watermark": {{
    "detected": <true|false>,
    "x": <0.0~1.0>,
    "y": <0.0~1.0>,
    "w": <0.0~1.0>,
    "h": <0.0~1.0>,
    "description": "<설명>"
  }}
}}

score 기준:
- 0.85+: 해당 제품이 명확하게 보임
- 0.65-0.85: 제품이 보이나 일부 불확실
- 0.40-0.65: 관련성 낮거나 품질 문제 있음
- 0.40 미만: 무관한 이미지 또는 심각한 품질 문제

issues 기준:
- "watermark": 눈에 띄는 텍스트/로고 워터마크 존재
- "mismatch": 제품과 관련 없는 이미지
- "low_quality": 흐릿하거나 너무 어둡거나 해상도가 낮음
- "cropped": 제품이 잘려서 보임"""


# ── Single image analysis ─────────────────────────────────────────────────────

def _analyze_single(url: str, item: CelebItem, client) -> CandidateScore:
    """Call GPT-4o vision to score one image against item context."""
    fetched = _fetch_base64(url)
    if fetched is None:
        return CandidateScore(
            url=url, score=0.0,
            issues=["download_failed"],
            explanation="이미지 다운로드 실패",
        )

    b64, mime = fetched
    prompt = _make_prompt(item)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}",
                            "detail": "low",      # low detail = fewer tokens
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=350,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "{}").strip()
        data = json.loads(raw)
    except Exception as e:
        return CandidateScore(
            url=url, score=0.4,
            issues=[],
            explanation=f"분석 오류: {e}",
        )

    score = float(data.get("score", 0.4))
    score = max(0.0, min(1.0, score))
    issues: list[str] = data.get("issues", [])
    explanation: str = data.get("explanation", "")

    watermark_region: Optional[WatermarkRegion] = None
    wm = data.get("watermark", {})
    if wm.get("detected") and wm.get("w", 0) > 0.01 and wm.get("h", 0) > 0.01:
        watermark_region = WatermarkRegion(
            x=float(wm.get("x", 0.0)),
            y=float(wm.get("y", 0.0)),
            w=float(wm.get("w", 0.1)),
            h=float(wm.get("h", 0.05)),
            description=str(wm.get("description", "")),
        )
        if "watermark" not in issues:
            issues.append("watermark")

    return CandidateScore(
        url=url,
        score=score,
        issues=issues,
        explanation=explanation,
        watermark_region=watermark_region,
    )


# ── Per-item analysis ─────────────────────────────────────────────────────────

def analyze_item(index: int, item: CelebItem, client) -> ItemImageAnalysis:
    """Analyze and rank all candidate images for one item."""
    # Deduplicate + limit candidates
    seen: set[str] = set()
    all_urls: list[str] = []
    for url in (item.image_urls or []) + (item.candidate_image_urls or []):
        if url and url not in seen:
            seen.add(url)
            all_urls.append(url)
            if len(all_urls) >= MAX_CANDIDATES_PER_ITEM:
                break

    if not all_urls:
        return ItemImageAnalysis(
            item_index=index,
            best_url="",
            best_score=0.0,
            needs_review=True,
            candidates=[],
        )

    scored: list[CandidateScore] = [
        _analyze_single(url, item, client)
        for url in all_urls
    ]

    # Sort: score DESC, then prefer no-mismatch, then fewest issues overall
    scored.sort(key=lambda c: (
        -c.score,
        "mismatch" in c.issues,        # False(0) before True(1) → no-mismatch first
        "download_failed" in c.issues, # de-prioritise failed downloads
        len(c.issues),                 # fewer issues first at same score
    ))

    best = scored[0]
    needs_review = (
        best.score < NEEDS_REVIEW_THRESHOLD
        or bool(best.issues)
    )

    return ItemImageAnalysis(
        item_index=index,
        best_url=best.url,
        best_score=best.score,
        needs_review=needs_review,
        candidates=scored,
    )


# ── Batch analysis ────────────────────────────────────────────────────────────

def batch_analyze_items(
    items: list[CelebItem],
    client,
    on_progress=None,
) -> list[ItemImageAnalysis]:
    """
    Analyze all items sequentially.
    on_progress(index, total, analysis) called after each item.
    Respects pipeline cancel token.
    """
    from services.cancel_token import pipeline as _ct

    results: list[ItemImageAnalysis] = []
    total = len(items)

    for i, item in enumerate(items):
        _ct.check()
        try:
            result = analyze_item(i, item, client)
        except Exception as e:
            result = ItemImageAnalysis(
                item_index=i,
                best_url=(item.image_urls[0] if item.image_urls else ""),
                best_score=0.0,
                needs_review=True,
                candidates=[],
            )

        results.append(result)
        if on_progress:
            on_progress(i, total, result)

    return results
