import pandas as pd
from openai import OpenAI
from typing import List, Dict


def extract_celeb(title: str, client: OpenAI) -> str:
    """Extract celebrity name(s) from a blog post title using GPT."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "문구를 입력하면 그 문구로부터 연예인의 이름을 찾아서 출력해줘. "
                        "문장이 나와도 문장에 대답하지 말고, 해당 문장에 등장하는 연예인의 이름만 찾아서 출력해. "
                        "여러 명이면 쉼표로 구분해. 연예인이 없으면 빈 문자열만 출력해."
                    ),
                },
                {"role": "user", "content": "이달의소녀덤덤이달의소녀 롤링다이스로 롤아웃 풀세트 연봄빛 코드"},
                {"role": "assistant", "content": "이달의소녀"},
                {"role": "user", "content": "이도경5이도경이봉지아 1회 이도경의 봄 봄트 이도경이 착용한 올 봄 착용 시간 이도경의 분석 코드 의상"},
                {"role": "assistant", "content": "이도경, 봉지아"},
                {"role": "user", "content": "이재호 혼자사는 이민호 집 거실 뭐가있나요?"},
                {"role": "assistant", "content": "이재호"},
                {"role": "user", "content": title},
            ],
            temperature=1,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""


def get_trending_celebs(posts: List[Dict], client: OpenAI, top_n: int = 3) -> List[str]:
    """Return top-N trending celebrities from post titles."""
    celebs: List[str] = []
    for post in posts:
        result = extract_celeb(post["title"], client)
        if result:
            celebs.extend(c.strip() for c in result.split(",") if c.strip())

    if not celebs:
        return []

    counts = pd.Series(celebs).value_counts()
    return counts.index[:top_n].tolist()
