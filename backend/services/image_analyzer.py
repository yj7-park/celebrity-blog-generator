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
  "watermark_detected": <true|false>
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


_WATERMARK_LOCALIZE_PROMPT = """이 이미지에서 제3자가 삽입한 워터마크를 모두 찾아 각각의 정확한 바운딩박스를 반환하세요.

좌표 체계: 이미지 좌상단 (0,0) → 우하단 (1,1)
x = 워터마크 왼쪽 경계, y = 워터마크 위쪽 경계, w = 너비, h = 높이

JSON으로만 응답 (마크다운 없이):
{
  "watermarks": [
    {
      "x": <0.0~1.0>,
      "y": <0.0~1.0>,
      "w": <0.0~1.0>,
      "h": <0.0~1.0>,
      "description": "<위치와 내용 설명>"
    }
  ]
}

워터마크가 없으면: {"watermarks": []}

★ 워터마크로 판단하는 것:
- 이미지 위에 겹쳐진 반투명 또는 불투명 텍스트 (한글 쇼핑몰명, 블로그명, URL, © 표시 등)
- 이미지 모서리/중앙에 삽입된 로고나 도장
- 예: "궁금e장9포켓", "gettyimages", "shutterstock", "©", "www.xxx.com" 등

★ 워터마크가 아닌 것 (절대 포함 금지):
- "celeb.picks" — 이것은 이미지 하단 바에 있는 당사 서명이므로 반드시 제외
- 이미지의 실제 피사체 (제품, 의류, 인물, 배경)
- 이미지에 원래 포함된 브랜드 태그/라벨

★ 좌표 정확도:
- 텍스트/로고를 최대한 꼭 맞게 감싸도록 바운딩박스를 지정
- 여백을 너무 많이 주지 말 것 (정확할수록 제거 품질이 높아짐)
- 이미지 가장자리를 벗어나지 않도록 주의"""


# ── Single image analysis ─────────────────────────────────────────────────────

_CROP_REFINE_PROMPT = """이 이미지는 원본 이미지에서 잘라낸 부분입니다.
이 크롭 안에서 워터마크 텍스트/로고의 정확한 위치를 알려주세요.

좌표 체계: 이 크롭 이미지의 좌상단 (0,0) → 우하단 (1,1)

JSON으로만 응답 (마크다운 없이):
{
  "found": true,
  "x": <워터마크 왼쪽 경계, 0.0~1.0>,
  "y": <워터마크 위쪽 경계, 0.0~1.0>,
  "w": <너비, 0.0~1.0>,
  "h": <높이, 0.0~1.0>
}

워터마크가 없으면: {"found": false}

주의: "celeb.picks" 바는 워터마크가 아닙니다. 반드시 제외하세요.
텍스트를 최대한 꼭 맞게 감싸세요. 여백 최소화."""


def _ask_gpt_for_watermarks(b64: str, mime: str, client, detail: str = "high") -> list[dict]:
    """Single GPT call → raw list of watermark dicts."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{b64}", "detail": detail}},
                    {"type": "text", "text": _WATERMARK_LOCALIZE_PROMPT},
                ],
            }],
            max_tokens=400, temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        return data.get("watermarks", [])
    except Exception:
        return []


def _crop_and_refine(raw_b64: str, region: dict, client) -> Optional[dict]:
    """
    Crop the image to the rough region (with padding), ask GPT to precisely
    locate the watermark within the crop, then transform back to full coords.
    """
    try:
        raw_bytes = base64.b64decode(raw_b64)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        iw, ih = img.size

        # Expand region by 20% on each side for context
        pad = 0.20
        cx1 = max(0.0, region["x"] - pad)
        cy1 = max(0.0, region["y"] - pad)
        cx2 = min(1.0, region["x"] + region["w"] + pad)
        cy2 = min(1.0, region["y"] + region["h"] + pad)

        # Crop must be at least 80×40 px to be useful
        crop_w = int((cx2 - cx1) * iw)
        crop_h = int((cy2 - cy1) * ih)
        if crop_w < 80 or crop_h < 40:
            return None

        crop = img.crop((int(cx1 * iw), int(cy1 * ih),
                         int(cx2 * iw), int(cy2 * ih)))

        # Encode crop
        buf = io.BytesIO()
        crop.save(buf, format="JPEG", quality=90)
        crop_b64 = base64.b64encode(buf.getvalue()).decode()

        # Ask GPT for precise location within crop
        resp = _ask_gpt_single_refine(crop_b64, client)
        if not resp or not resp.get("found"):
            return None

        # Transform crop-relative coords → full image coords
        rx, ry = float(resp.get("x", 0)), float(resp.get("y", 0))
        rw, rh = float(resp.get("w", 0)), float(resp.get("h", 0))

        fx = cx1 + rx * (cx2 - cx1)
        fy = cy1 + ry * (cy2 - cy1)
        fw = rw * (cx2 - cx1)
        fh = rh * (cy2 - cy1)

        return {"x": fx, "y": fy, "w": fw, "h": fh,
                "description": region.get("description", "")}
    except Exception:
        return None


def _ask_gpt_single_refine(crop_b64: str, client) -> Optional[dict]:
    """Precise localization within a crop image."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{crop_b64}",
                                   "detail": "high"}},
                    {"type": "text", "text": _CROP_REFINE_PROMPT},
                ],
            }],
            max_tokens=120, temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return None


def _localize_watermarks(b64: str, mime: str, client) -> List[WatermarkRegion]:
    """
    Three-pass localization:
      Pass A: full image, high detail  → rough regions
      Pass B: per-region crop, high detail  → refined coordinates
    Returns WatermarkRegion list with sub-pixel-accurate boxes.
    """
    # Pass A: full image rough detection
    rough_list = _ask_gpt_for_watermarks(b64, mime, client, detail="high")
    if not rough_list:
        return []

    regions: List[WatermarkRegion] = []
    for rough in rough_list:
        rw = float(rough.get("w", 0))
        rh = float(rough.get("h", 0))
        if rw < 0.005 or rh < 0.005:
            continue

        # Pass B: crop refinement
        refined = _crop_and_refine(b64, rough, client)
        final = refined if refined else rough

        fw = float(final.get("w", 0))
        fh = float(final.get("h", 0))
        if fw < 0.005 or fh < 0.005:
            continue

        regions.append(WatermarkRegion(
            x=max(0.0, min(1.0, float(final.get("x", 0)))),
            y=max(0.0, min(1.0, float(final.get("y", 0)))),
            w=max(0.005, min(1.0, fw)),
            h=max(0.005, min(1.0, fh)),
            description=str(final.get("description", rough.get("description", ""))),
        ))

    return regions


def _analyze_single(url: str, item: CelebItem, client) -> CandidateScore:
    """
    Two-pass analysis:
      Pass 1 (low detail): scoring + issue detection (cheap)
      Pass 2 (high detail): watermark localization, only if watermark flagged
    """
    fetched = _fetch_base64(url)
    if fetched is None:
        return CandidateScore(
            url=url, score=0.0,
            issues=["download_failed"],
            explanation="이미지 다운로드 실패",
        )

    b64, mime = fetched

    # ── Pass 1: scoring ──────────────────────────────────────────────────────
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"},
                    },
                    {"type": "text", "text": _make_prompt(item)},
                ],
            }],
            max_tokens=200,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        return CandidateScore(url=url, score=0.4, issues=[], explanation=f"분석 오류: {e}")

    score = max(0.0, min(1.0, float(data.get("score", 0.4))))
    issues: list[str] = data.get("issues", [])
    explanation: str = data.get("explanation", "")

    # ── Pass 2: watermark localization (high detail) ─────────────────────────
    watermark_regions: List[WatermarkRegion] = []
    if data.get("watermark_detected") or "watermark" in issues:
        if "watermark" not in issues:
            issues.append("watermark")
        watermark_regions = _localize_watermarks(b64, mime, client)

    return CandidateScore(
        url=url,
        score=score,
        issues=issues,
        explanation=explanation,
        watermark_regions=watermark_regions,
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
