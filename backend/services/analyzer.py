"""Celebrity name extraction and trending analysis."""
from __future__ import annotations
from typing import Callable, List, Optional
from openai import OpenAI
from models.schemas import PostItem


def get_trending_celebs(
    posts: List[PostItem],
    client: OpenAI,
    top_n: int = 5,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    if not posts:
        return []

    titles_block = "\n".join(f"{i+1}. {p.title}" for i, p in enumerate(posts))

    if on_progress:
        on_progress(30, 100)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 연예 트렌드 분석 전문가입니다. 제공된 블로그 게시글 제목 목록을 분석하여 "
                    "현재 가장 많이 언급되거나 화제가 되고 있는 연예인(셀럽)들을 추출하세요.\n"
                    "규칙:\n"
                    "1. 제목에서 옷, 가방, 액세서리 정보가 포함된 연예인을 우선순위로 두세요.\n"
                    "2. 상위 연예인들의 이름을 중요도 순으로 나열하세요.\n"
                    "3. 이름만 쉼표(,)로 구분하여 정확히 출력하세요. 부가 설명은 생략하세요."
                ),
            },
            {"role": "user", "content": f"분석할 제목 목록:\n{titles_block}"},
        ],
        temperature=0.3,
    )

    if on_progress:
        on_progress(90, 100)

    content = (resp.choices[0].message.content or "").strip()
    celebs = [
        c.strip().lstrip("0123456789. ")
        for c in content.replace("\n", ",").split(",")
    ]
    celebs = [c for c in celebs if 1 < len(c) < 12]
    # Deduplicate preserving order
    seen: set[str] = set()
    unique = [c for c in celebs if not (c in seen or seen.add(c))]  # type: ignore

    if on_progress:
        on_progress(100, 100)

    return unique[:top_n]
