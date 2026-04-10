from openai import OpenAI
from typing import Dict, List


def generate_blog_post(
    celeb: str,
    items: Dict[str, str],
    content_snippets: List[str],
    client: OpenAI,
) -> str:
    """Generate a Korean blog post about a celebrity's fashion/lifestyle items."""
    items_text = (
        "\n".join(f"- {k}: {v}" for k, v in list(items.items())[:20])
        if items
        else "수집된 아이템 없음"
    )
    context_text = "\n\n".join(content_snippets[:3])[:2000] if content_snippets else ""

    prompt = f"""연예인 '{celeb}'에 관한 패션/라이프스타일 블로그 게시글을 작성해주세요.

수집된 아이템 정보:
{items_text}

참고 블로그 내용:
{context_text if context_text else "(없음)"}

다음 형식으로 작성해주세요:
1. SEO 최적화된 제목
2. 흥미로운 도입부 (2-3문장)
3. 주요 아이템 3-5개 각각 상세 소개
4. 마무리 문단
5. 관련 해시태그 10개

독자가 구매 욕구를 느낄 수 있도록 생동감 있게 작성해주세요."""

    try:
        response = client.chat.completions.create(
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
        return response.choices[0].message.content
    except Exception as e:
        return f"블로그 생성 오류: {e}"
