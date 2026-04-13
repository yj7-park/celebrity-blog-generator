"""Blog post generation from CelebItem list.

Outputs:
  - blog_post : raw text for preview
  - title     : SEO-optimised post title
  - elements  : List[BlogElement] ready for NaverBlogWriter
"""
from __future__ import annotations
import json
from typing import List
from openai import OpenAI
from models.schemas import BlogElement, CelebItem

AFFILIATE_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, "
    "이에 따른 일정액의 수수료를 제공받습니다."
)


def generate_blog_post(items: List[CelebItem], client: OpenAI) -> str:
    """Return raw text blog post (for preview / legacy callers)."""
    result = _generate(items, client)
    return result["blog_post"]


def generate_blog_elements(
    items: List[CelebItem], client: OpenAI
) -> dict:
    """Return {'title': str, 'blog_post': str, 'elements': List[BlogElement]}."""
    return _generate(items, client)


# ── Internal ───────────────────────────────────────────────────────────────────

def _generate(items: List[CelebItem], client: OpenAI) -> dict:
    if not items:
        empty: List[BlogElement] = [
            BlogElement(type="text", content="생성할 아이템 정보가 없습니다.")
        ]
        return {
            "title": "연예인 아이템 소개",
            "blog_post": "생성할 아이템 정보가 없습니다.",
            "elements": empty,
        }

    # Pick most-represented celeb
    from collections import defaultdict
    grouped: dict[str, List[CelebItem]] = defaultdict(list)
    for it in items:
        grouped[it.celeb].append(it)
    main_celeb, main_items = max(grouped.items(), key=lambda kv: len(kv[1]))

    def _sanitize(s: str) -> str:
        """Remove control characters (NUL, etc.) that break JSON serialization."""
        return "".join(c for c in s if c >= " " or c in "\n\r\t")

    items_text = "\n".join(
        f"- [{_sanitize(it.category)}] {_sanitize(it.product_name)}"
        f" (키워드: {', '.join(_sanitize(k) for k in it.keywords[:3])})"
        for it in main_items[:10]
    )

    # ── Step 1: structured JSON from LLM ──────────────────────────────────────
    structure_prompt = f"""연예인 '{main_celeb}'의 착용·사용 아이템에 관한 블로그 포스트 구성 데이터를 JSON으로 반환하세요.

수집된 아이템:
{items_text}

다음 JSON 형식을 **반드시** 지켜주세요. 마크다운 코드블록 없이 JSON만 반환하세요:
{{
  "title": "SEO 최적화 제목 (40자 이내)",
  "intro": "흥미로운 도입부 2~3문장. 독자가 계속 읽고 싶게 만드세요.",
  "items": [
    {{
      "header": "아이템명 (카테고리)",
      "description": "아이템 상세 설명 3~5문장. 방송 착용 맥락, 스타일 포인트, 구매 욕구를 자극하는 내용."
    }}
  ],
  "outro": "마무리 2~3문장. 구매를 자연스럽게 유도.",
  "hashtags": "#연예인명 #패션 #아이템 등 10개 해시태그 공백 구분"
}}"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 연예인 패션과 라이프스타일 아이템을 소개하는 인기 블로거입니다. "
                        "독자가 구매 욕구를 느낄 수 있도록 생동감 있고 친근하게 작성합니다."
                    ),
                },
                {"role": "user", "content": structure_prompt},
            ],
            temperature=0.8,
            max_tokens=3000,
        )
        raw = resp.choices[0].message.content or "{}"
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        structured = json.loads(raw)
    except Exception as e:
        fallback_text = f"블로그 생성 오류: {e}"
        return {
            "title": f"{main_celeb} 아이템 모음",
            "blog_post": fallback_text,
            "elements": [BlogElement(type="text", content=fallback_text)],
        }

    title: str = structured.get("title", f"{main_celeb} 착용 아이템 모음")
    intro: str = structured.get("intro", "")
    item_blocks: list = structured.get("items", [])
    outro: str = structured.get("outro", "")
    hashtags: str = structured.get("hashtags", "")

    # ── Step 2: Build BlogElement list ────────────────────────────────────────
    elements: List[BlogElement] = []

    # 대가성 문구 (법적 의무 — 최상단)
    elements.append(BlogElement(type="text", content=AFFILIATE_DISCLOSURE))

    # 도입부
    if intro:
        elements.append(BlogElement(type="text", content=intro))

    # 아이템별 블록
    for idx, item_obj in enumerate(item_blocks):
        source_item = main_items[idx] if idx < len(main_items) else None

        header_text = item_obj.get("header", "")
        description = item_obj.get("description", "")

        if header_text:
            elements.append(BlogElement(type="header", content=header_text))
        if description:
            elements.append(BlogElement(type="text", content=description))

        # 쿠팡 링크가 있으면 구매 버튼 삽입
        if source_item and source_item.link_url:
            elements.append(BlogElement(type="url_text", content=source_item.link_url))

    # 마무리
    if outro:
        elements.append(BlogElement(type="text", content=outro))

    # 해시태그
    if hashtags:
        elements.append(BlogElement(type="text", content=hashtags))

    # ── Step 3: Build raw text for preview ────────────────────────────────────
    lines = [AFFILIATE_DISCLOSURE, "", intro, ""]
    for el in elements:
        if el.type == "header":
            lines.append(f"\n### {el.content}")
        elif el.type == "text" and el.content not in (AFFILIATE_DISCLOSURE, intro, outro, hashtags):
            lines.append(el.content)
        elif el.type == "url_text":
            lines.append(f"[최저가 구매하러 가기]({el.content})")
    lines += ["", outro, "", hashtags]
    blog_post = "\n".join(lines)

    return {"title": title, "blog_post": blog_post, "elements": elements}
