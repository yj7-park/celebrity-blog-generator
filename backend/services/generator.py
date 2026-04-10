"""Blog post generation from CelebItem list."""
from __future__ import annotations
from typing import List
from openai import OpenAI
from models.schemas import CelebItem


def generate_blog_post(items: List[CelebItem], client: OpenAI) -> str:
    if not items:
        return "생성할 아이템 정보가 없습니다."

    # Group by celeb, pick most-represented
    from collections import defaultdict
    grouped: dict[str, List[CelebItem]] = defaultdict(list)
    for it in items:
        grouped[it.celeb].append(it)

    main_celeb, main_items = max(grouped.items(), key=lambda kv: len(kv[1]))

    items_text = "\n".join(
        f"- [{it.category}] {it.product_name} (키워드: {', '.join(it.keywords[:3])})"
        for it in main_items[:10]
    )

    prompt = f"""연예인 '{main_celeb}'의 착용·사용 아이템에 관한 블로그 포스트를 작성해주세요.

수집된 아이템:
{items_text}

형식:
1. SEO 최적화 제목
2. 흥미로운 도입부 (2~3문장)
3. 아이템별 상세 소개 (각 아이템마다 카테고리·특징 포함)
4. 마무리 문단
5. 해시태그 10개

독자가 구매 욕구를 느낄 수 있도록 생동감 있게 작성해주세요."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 연예인 패션과 라이프스타일 아이템을 소개하는 인기 블로거입니다.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=3000,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"블로그 생성 오류: {e}"
