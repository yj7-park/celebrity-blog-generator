"""Blog post generation from CelebItem list.

Outputs
-------
title     : SEO-optimised post title
blog_post : preview text (markdown-ish, for UI display only)
elements  : List[BlogElement] ready for NaverBlogWriter

Anti-SLOP strategy
------------------
The system prompt forces the LLM into the persona of a real Korean lifestyle
blogger — concrete scene references, varied sentence lengths, honest price
comments, and strict prohibitions on AI clichés.
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

# 대가성 문구 이미지 경로 (텍스트 대신 이미지로 삽입 — 검색 노출 최적화)
from pathlib import Path as _Path
AFFILIATE_DISCLOSURE_IMAGE = str(
    _Path(__file__).resolve().parents[1] / "static" / "assets" / "affiliate_disclosure.png"
)

# ── Anti-SLOP system prompt ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
당신은 '연주'라는 28살 직장인 여성 블로거입니다. 드라마와 패션에 진심이고,
네이버 블로그에 연예인 착용 아이템 소개 글을 씁니다.

[출력 포맷 — 네이버 스마트에디터 기준]
- 중요 단어(브랜드명, 제품명, 핵심 키워드)는 앞뒤를 `백틱`으로 감싸세요 → 굵게 표시됨
  예시: "`발렌티노` 베이지 토트백이 21세기대군부인 2회에서..."
- 줄바꿈이 필요한 곳에 실제 \n 사용 (마크다운 헤더 ## 사용 금지)
- URL이나 이미지 경로는 포함하지 마세요 — 코드에서 자동 삽입

[필수 말투]
- 친근한 해요체 (합니다체·반말 모두 금지)
- 문장 끝을 "~했어요", "~이에요", "~거든요", "~더라고요", "~해요~", "~한 것 같아요" 등으로 자연스럽게 변화
- "진짜", "완전", "솔직히", "근데", "이게" 같은 구어체 표현 자연스럽게 사용
- 각 아이템 설명은 반드시 다른 방식으로 시작 (같은 도입 패턴 반복 금지)
- 짧은 문장(5-8자)과 긴 문장(20-30자)을 불규칙하게 섞기
- 예시: "이 장면 나오자마자 캡처했어요", "진짜 심장 쫄았거든요~", "이 백 보자마자 바로 찾아봤어요"

[절대 금지]
- "완벽한", "훌륭한", "뛰어난", "탁월한", "놀라운" 같은 빈 찬사 형용사
- "첫째로 / 둘째로 / 마지막으로" 나열 패턴
- "뿐만 아니라", "또한", "그뿐만 아니라" 같은 작문 접속사
- 모든 아이템을 동일한 길이로 균등하게 설명하는 것
- "오늘은 ~ 소개해 드릴게요" 형태의 판에 박힌 도입부

[필수 포함 내용]
- 아이템이 나온 드라마/예능명과 에피소드 (keywords에서 추출)
- 구체적인 착장 포인트 (색감, 소재, 매치 방법)
- 솔직한 한마디: 가격대 현실 코멘트, 구하기 어렵다거나, 대안이 있다거나
- 개인적인 감상 ("이 장면에서 진짜 심장 쫄았어요~", "이 백 나오자마자 캡처했어요")

[해시태그]
네이버 블로그 실사용 스타일 — 드라마명, 연예인명, 아이템 키워드, 10-12개
"""

# ── Public API ────────────────────────────────────────────────────────────────

def generate_blog_post(items: List[CelebItem], client: OpenAI) -> str:
    """Return raw text blog post (for preview / legacy callers)."""
    return _generate(items, client)["blog_post"]


def generate_blog_elements(items: List[CelebItem], client: OpenAI,
                           image_placement: str = "두괄식") -> dict:
    """Return {'title', 'blog_post', 'elements': List[BlogElement]}.

    image_placement:
        "두괄식" — image appears BEFORE the body text (default, visual-first)
        "미괄식" — image appears AFTER  the body text (narrative-first)
    """
    return _generate(items, client, image_placement=image_placement)


# ── Internal ───────────────────────────────────────────────────────────────────

def _sanitize(s: str) -> str:
    """Remove NUL / control characters that break JSON serialisation."""
    return "".join(c for c in s if c >= " " or c in "\n\r\t")


def _generate(items: List[CelebItem], client: OpenAI,
              image_placement: str = "두괄식") -> dict:
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

    # Build item context for the prompt
    items_context = []
    for i, it in enumerate(main_items[:8]):
        kw_str = ", ".join(_sanitize(k) for k in it.keywords[:4])
        items_context.append(
            f"[아이템 {i+1}]\n"
            f"  카테고리: {_sanitize(it.category)}\n"
            f"  제품명: {_sanitize(it.product_name)}\n"
            f"  이슈 키워드: {kw_str or '(없음)'}\n"
            f"  쿠팡 링크: {'있음' if it.link_url else '없음'}\n"
            f"  이미지: {'있음' if it.processed_image_path or it.image_urls else '없음'}"
        )
    items_text = "\n\n".join(items_context)

    # ── Step 1: structured JSON from LLM ──────────────────────────────────────
    structure_prompt = f"""연예인 '{main_celeb}'의 착용·사용 아이템 소개 블로그 포스트를 작성해주세요.

수집된 아이템 정보:
{items_text}

다음 JSON 형식으로 **마크다운 코드블록 없이** 반환하세요:
{{
  "title": "SEO 최적화 제목 — 연예인명 + 아이템 키워드 포함, 35자 이내",
  "intro": "도입부 2-3문장. 드라마/예능 화제성으로 시작. 독자가 '맞아 나도 그 장면!' 하게 만들기.",
  "items": [
    {{
      "header": "[카테고리] 제품명",
      "body": "2-4문장 설명. 첫 문장은 반드시 이슈 키워드(드라마/프로그램명, 장면)로 시작. 구체적 스타일 포인트 포함.",
      "honest_note": "가격·구매 관련 솔직한 한마디 (1문장, 없으면 빈 문자열)"
    }}
  ],
  "outro": "마무리 2-3문장. 구매를 억지로 밀어붙이지 말고 자연스럽게.",
  "hashtags": "#드라마명 #연예인명 #아이템 등 10-12개 해시태그 공백 구분"
}}

시스템 지침을 반드시 따르세요 — SLOP 패턴 사용 시 전체 답변을 재생성합니다."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": structure_prompt},
            ],
            temperature=0.85,
            max_tokens=3500,
        )
        raw = (resp.choices[0].message.content or "{}").strip()
        # Strip markdown code fences if present
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

    # ── Step 2: Build BlogElement list (Naver-compatible) ─────────────────────
    elements: List[BlogElement] = []

    # 대가성 문구 이미지 (법적 의무 — 최상단, 텍스트 대신 이미지로 삽입)
    elements.append(BlogElement(type="image", content=AFFILIATE_DISCLOSURE_IMAGE))

    # 도입부
    if intro:
        elements.append(BlogElement(type="text", content=intro))

    # 아이템별 블록 조립
    # 두괄식: divider → header → 이미지 → 본문 → callout → 구매버튼
    # 미괄식: divider → header → 본문 → callout → 이미지 → 구매버튼
    is_dugowal = (image_placement != "미괄식")

    for idx, item_obj in enumerate(item_blocks):
        src = main_items[idx] if idx < len(main_items) else None

        header_text = item_obj.get("header", "")
        body = item_obj.get("body", "")
        honest_note = item_obj.get("honest_note", "")

        # 이미지 element 조립 (공통)
        def _img_el():
            if src and src.processed_image_path:
                return BlogElement(type="image", content=src.processed_image_path)
            elif src and src.image_urls:
                return BlogElement(type="image", content=src.image_urls[0])
            return None

        # 아이템 구분선
        elements.append(BlogElement(type="divider", content="line2"))

        if header_text:
            elements.append(BlogElement(type="header", content=header_text))

        if is_dugowal:
            # 두괄식: 이미지 먼저
            img_el = _img_el()
            if img_el:
                elements.append(img_el)
            if body.strip():
                elements.append(BlogElement(type="text", content=body.strip()))
        else:
            # 미괄식: 본문 먼저
            if body.strip():
                elements.append(BlogElement(type="text", content=body.strip()))
            img_el = _img_el()
            if img_el:
                elements.append(img_el)

        # 솔직한 한마디 → postit callout (항상 이미지 뒤)
        if honest_note.strip():
            elements.append(BlogElement(
                type="callout",
                content=honest_note.strip(),
                style="quotation_postit",
            ))

        # 쿠팡 구매 버튼
        if src and src.link_url:
            elements.append(BlogElement(type="url_text", content=src.link_url))

    # 마무리 앞 구분선
    if outro:
        elements.append(BlogElement(type="divider", content="line2"))
        elements.append(BlogElement(type="text", content=outro))

    # 해시태그
    if hashtags:
        elements.append(BlogElement(type="text", content=hashtags))

    # ── Step 3: Build raw text for preview ────────────────────────────────────
    lines = ["[대가성문구 이미지]", "", intro, ""]
    for el in elements:
        if el.type == "header":
            lines.append(f"\n### {el.content}")
        elif el.type == "image":
            lines.append(f"[이미지: {el.content}]")
        elif el.type == "divider":
            lines.append("\n─────────────────────────────\n")
        elif el.type == "callout":
            lines.append(f"\n💡 {el.content}\n")
        elif el.type == "text" and el.content not in (intro, outro, hashtags):
            lines.append(el.content)
        elif el.type == "url_text":
            lines.append(f"[최저가 구매하러 가기]({el.content})")
    lines += ["", outro, "", hashtags]
    blog_post = "\n".join(lines)

    # Parse hashtags string → clean tag list (strip #, split on whitespace/comma)
    import re as _re
    _raw_tags = _re.split(r"[\s,]+", hashtags) if hashtags else []
    tags = [t.lstrip("#").strip() for t in _raw_tags if t.lstrip("#").strip()]

    return {"title": title, "blog_post": blog_post, "elements": elements, "tags": tags}
