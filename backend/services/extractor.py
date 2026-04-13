"""
LLM-based structured item extraction from scraped Naver blog posts.
Ported from standalone/src/lib/extractor.ts
"""
from __future__ import annotations
import json, re
from typing import List, Optional
from openai import OpenAI
from models.schemas import CelebItem, ScrapedPostData
from services.url_resolver import resolve, is_short_url

CATEGORY_GUIDE = """
카테고리 기준:
가방(핸드백/숄더백/백팩/클러치), 신발(스니커즈/플랫/힐/부츠/샌들),
의류(코트/자켓/가디건/니트/셔츠/원피스/팬츠 등),
뷰티(스킨케어/메이크업/향수/헤어), 식품(음식/영양제/음료),
생활(주방/청소/가전/인테리어), 액세서리(주얼리/시계/선글라스/벨트), 기타
"""

SYSTEM_PROMPT = f"""당신은 연예인 협찬·착용 아이템 정보를 블로그에서 구조화 추출하는 전문가입니다.

블로그 포스트의 순서 블록(TEXT/IMAGE_N이 등장 순서대로 나열)을 분석하여
각 연예인이 착용·사용한 아이템을 JSON 배열로 추출하세요.

{CATEGORY_GUIDE}

출력 형식 (순수 JSON 배열):
[
  {{
    "celeb": "연예인 이름",
    "category": "카테고리",
    "product_name": "브랜드명 + 제품명 (최대한 구체적으로)",
    "image_indices": [0, 2],
    "keywords": ["방송명/회차", "키워드"],
    "link_text": "▶...보러가기 형태 텍스트"
  }}
]

규칙:
1. image_indices: IMAGE_N 레이블 중 해당 제품과 가장 가까이 있는 인덱스
2. 제품명: 브랜드+모델명 포함, 모르면 텍스트 설명으로
3. 연예인 이름 불명확하면 제외
4. JSON 배열만 출력 (마크다운 코드블록 없이)"""


def _build_prompt(scraped: ScrapedPostData):
    img_map: dict[int, str] = {}
    img_counter = 0
    block_lines: list[str] = []

    for blk in scraped.ordered_blocks[:120]:
        if blk.type == "image" and blk.url:
            img_map[img_counter] = blk.url
            block_lines.append(f"[IMAGE_{img_counter}]")
            img_counter += 1
        elif blk.type == "text" and blk.content:
            block_lines.append(f"TEXT: {blk.content[:100]}")

    # fallback: paragraphs + imageUrls
    if img_counter == 0 and scraped.image_urls:
        for i, url in enumerate(scraped.image_urls):
            img_map[i] = url
        for p in scraped.paragraphs[:40]:
            block_lines.append(f"TEXT: {p[:100]}")
        for i in range(len(scraped.image_urls)):
            block_lines.append(f"[IMAGE_{i}]")

    link_lines = [
        f"  [{lk.get('text','')[:25]}] → {lk.get('href','')[:60]}"
        for lk in scraped.links[:10]
    ]

    prompt = (
        f"## 제목\n{scraped.title}\n\n"
        f"## 순서 블록\n{chr(10).join(block_lines)}\n\n"
        f"## 링크\n{chr(10).join(link_lines)}"
    )
    return prompt, img_map


def _safe_parse_json(raw: str) -> list:
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
    except json.JSONDecodeError:
        m = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if m:
            try:
                arr = json.loads(m.group(0))
                if isinstance(arr, list):
                    return [x for x in arr if isinstance(x, dict)]
            except Exception:
                pass
    return []


def extract_from_post(scraped: ScrapedPostData, client: OpenAI) -> List[CelebItem]:
    prompt, img_map = _build_prompt(scraped)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    raw = resp.choices[0].message.content or ""
    items_raw = _safe_parse_json(raw)

    results: List[CelebItem] = []
    for item in items_raw:
        indices = item.get("image_indices", [])
        if not isinstance(indices, list):
            indices = []
        image_urls = [img_map[i] for i in indices if isinstance(i, int) and i in img_map]

        link_text = str(item.get("link_text", ""))
        # Try to match by link_text, fall back to first available link
        matched_link = next(
            (lk.get("href", "") for lk in scraped.links
             if link_text and link_text[:8] in lk.get("text", "")),
            "",
        )
        if not matched_link and scraped.links:
            matched_link = scraped.links[0].get("href", "")

        # Resolve short URLs (vvd.bz, bit.ly, han.gl, etc.) to final destination
        if matched_link and is_short_url(matched_link):
            matched_link = resolve(matched_link)

        celeb = str(item.get("celeb", "")).strip()
        product_name = str(item.get("product_name", "")).strip()
        if not celeb or not product_name:
            continue

        keywords = item.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []

        results.append(CelebItem(
            celeb=celeb,
            category=str(item.get("category", "기타")),
            product_name=product_name,
            image_urls=image_urls,
            keywords=[str(k) for k in keywords],
            link_url=matched_link,
            source_title=scraped.title,
            source_url=scraped.post_url,
        ))
    return results


def extract_items_from_posts(
    scraped_posts: List[ScrapedPostData],
    client: OpenAI,
    on_progress=None,
) -> List[CelebItem]:
    all_items: List[CelebItem] = []

    for i, post in enumerate(scraped_posts):
        try:
            items = extract_from_post(post, client)
            all_items.extend(items)
        except Exception:
            pass
        if on_progress:
            on_progress(i + 1, len(scraped_posts))

    # Deduplicate by celeb + product_name
    seen: set[str] = set()
    deduped: List[CelebItem] = []
    for item in all_items:
        key = f"{item.celeb}::{item.product_name}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped
