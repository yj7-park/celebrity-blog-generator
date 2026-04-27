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


def _build_prompt(scraped: ScrapedPostData, image_mapping: str = "두괄식"):
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

    # Per-source image placement hint
    if image_mapping == "미괄식":
        mapping_hint = (
            "\n\n[소스 블로그 패턴: 미괄식] "
            "이 블로그는 이미지를 먼저 올리고 제품 설명을 아래에 씁니다. "
            "(IMAGE → TEXT 순서) image_indices 선택 시 텍스트 바로 앞 이미지를 우선하세요."
        )
    else:
        mapping_hint = (
            "\n\n[소스 블로그 패턴: 두괄식] "
            "이 블로그는 제품 설명을 먼저 쓰고 이미지를 아래에 올립니다. "
            "(TEXT → IMAGE 순서) image_indices 선택 시 텍스트 바로 뒤 이미지를 우선하세요."
        )

    prompt = (
        f"## 제목\n{scraped.title}{mapping_hint}\n\n"
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


def extract_from_post(scraped: ScrapedPostData, client: OpenAI,
                      image_mapping: str = "두괄식") -> List[CelebItem]:
    prompt, img_map = _build_prompt(scraped, image_mapping)

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

        # Primary images: LLM-selected
        image_urls = [img_map[i] for i in indices if isinstance(i, int) and i in img_map]

        # Candidate images: ±3 neighbors around each selected index
        candidate_set: list[str] = []
        max_idx = max(img_map.keys()) if img_map else -1
        for sel_idx in (indices if indices else []):
            if not isinstance(sel_idx, int):
                continue
            for offset in range(-3, 4):   # -3 to +3
                cand_idx = sel_idx + offset
                if cand_idx in img_map and img_map[cand_idx] not in candidate_set:
                    candidate_set.append(img_map[cand_idx])
        # If no LLM indices, include all images as candidates
        if not indices:
            candidate_set = list(img_map.values())

        link_text = str(item.get("link_text", ""))
        # Try to match by link_text only — no fallback to first link (avoids wrong URLs)
        matched_link = next(
            (lk.get("href", "") for lk in scraped.links
             if link_text and link_text[:8] in lk.get("text", "")),
            "",
        )

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
            candidate_image_urls=candidate_set,
            keywords=[str(k) for k in keywords],
            link_url=matched_link,
            source_title=scraped.title,
            source_url=scraped.post_url,
        ))
    return results


def _normalize_name(name: str) -> str:
    """Lowercase + remove non-alphanumeric for product-name grouping."""
    return re.sub(r"[^a-z0-9가-힣]", "", name.lower())


def semantic_deduplicate_items(items: List[CelebItem], client: OpenAI) -> List[CelebItem]:
    """Use LLM to identify and merge items that are semantically the same product."""
    if not items:
        return []
    
    # Group by celeb first to reduce prompt size
    celeb_groups: dict[str, List[CelebItem]] = {}
    for it in items:
        celeb_groups.setdefault(it.celeb, []).append(it)
    
    final_results: List[CelebItem] = []
    
    for celeb, group in celeb_groups.items():
        if len(group) < 2:
            final_results.extend(group)
            continue
            
        # Prepare list for LLM
        item_list = []
        for i, it in enumerate(group):
            item_list.append({
                "id": i,
                "name": it.product_name,
                "category": it.category
            })
            
        prompt = f"""다음은 셀럽 '{celeb}'이 착용한 아이템 목록입니다. 
동일한 제품인 것들을 찾아 그룹화하세요. 브랜드명이 생략되었거나 표현이 약간 달라도 실질적으로 같은 모델이면 하나로 합쳐야 합니다.

아이템 목록:
{json.dumps(item_list, ensure_ascii=False, indent=2)}

출력 형식 (JSON 배열):
[
  [0, 2], // 0번과 2번이 같은 제품인 경우
  [1],    // 1번이 독자적인 제품인 경우
  ...
]
순수 JSON 배열만 응답하세요."""

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"} if False else None # older compat
            )
            raw = resp.choices[0].message.content or "[]"
            # Basic cleaning if LLM returned markdown
            if "```" in raw:
                raw = re.sub(r"```json\s*", "", raw)
                raw = re.sub(r"```\s*", "", raw).strip()
            
            # Simple check for the list of lists structure
            groups_indices = json.loads(raw)
            if not isinstance(groups_indices, list):
                # Fallback to normalized grouping if LLM fails
                final_results.extend(group)
                continue
                
            for indices in groups_indices:
                if not indices: continue
                # Merge items in this group
                base_item = group[indices[0]].model_copy()
                for idx in indices[1:]:
                    other = group[idx]
                    # Merge logic
                    seen_imgs = set(base_item.image_urls)
                    for u in other.image_urls:
                        if u and u not in seen_imgs:
                            base_item.image_urls.append(u)
                            seen_imgs.add(u)
                    
                    seen_cands = set(base_item.candidate_image_urls)
                    for u in other.candidate_image_urls:
                        if u and u not in seen_cands:
                            base_item.candidate_image_urls.append(u)
                            seen_cands.add(u)
                            
                    seen_kws = set(base_item.keywords)
                    for kw in other.keywords:
                        if kw and kw not in seen_kws:
                            base_item.keywords.append(kw)
                            seen_kws.add(kw)
                    
                    if len(other.product_name) > len(base_item.product_name):
                        base_item.product_name = other.product_name
                
                final_results.append(base_item)
        except Exception:
            # Fallback
            final_results.extend(group)
            
    return final_results


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

    # 1. First pass: normalization-based grouping (fast)
    groups: dict[str, CelebItem] = {}
    for item in all_items:
        key = f"{item.celeb}::{_normalize_name(item.product_name)}"
        if key not in groups:
            groups[key] = item
        else:
            existing = groups[key]
            # Merge logic
            seen_imgs = set(existing.image_urls)
            for url in item.image_urls:
                if url and url not in seen_imgs:
                    existing.image_urls.append(url)
                    seen_imgs.add(url)
            seen_cands = set(existing.candidate_image_urls)
            for url in item.candidate_image_urls:
                if url and url not in seen_cands:
                    existing.candidate_image_urls.append(url)
                    seen_cands.add(url)
            seen_kws = set(existing.keywords)
            for kw in item.keywords:
                if kw and kw not in seen_kws:
                    existing.keywords.append(kw)
                    seen_kws.add(kw)
            if len(item.product_name) > len(existing.product_name):
                existing.product_name = item.product_name

    # 2. Second pass: semantic deduplication (smart)
    return semantic_deduplicate_items(list(groups.values()), client)
