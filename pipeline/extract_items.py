"""
Phase 2: LLM 구조화 추출 (버그 수정 + 이미지 매칭 강화)
ordered_blocks (텍스트+이미지 순서) 를 LLM에 제공해서 매핑 정확도 향상.
"""
import json, os, sys, re
import requests, urllib3
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding="utf-8")

from openai import OpenAI

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
OUT_DIR      = os.path.join(os.path.dirname(__file__), "extracted")
os.makedirs(OUT_DIR, exist_ok=True)


def get_client():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    api_key = None
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith(("openai_key", "OPENAI_API_KEY", "openai_token")):
                    api_key = line.split("=", 1)[1].strip()
    except Exception:
        pass
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 없음")
    return OpenAI(api_key=api_key)


CATEGORY_GUIDE = """
카테고리 기준:
가방(핸드백/숄더백/백팩/클러치), 신발(스니커즈/플랫/힐/부츠),
의류(코트/자켓/가디건/니트/셔츠/원피스/팬츠 등),
뷰티(스킨케어/메이크업/향수), 식품(음식/영양제/음료),
생활(주방/청소/가전/인테리어), 액세서리(주얼리/시계/선글라스), 기타
"""

SYSTEM_PROMPT = f"""당신은 연예인 협찬/사용 아이템 정보를 블로그에서 구조화 추출하는 전문가입니다.

블로그 포스트의 [순서 블록] (텍스트/이미지가 등장 순서대로 나열됨)을 분석하여
각 연예인이 착용·사용한 아이템을 JSON 배열로 추출하세요.

{CATEGORY_GUIDE}

출력 형식 (순수 JSON 배열):
[
  {{
    "celeb": "연예인 이름",
    "category": "카테고리",
    "product_name": "브랜드명 + 제품명 (가능한 한 구체적으로)",
    "image_indices": [0, 2],
    "keywords": ["방송명/회차", "키워드"],
    "link_text": "구매 링크 텍스트 (▶...보러가기 형태)"
  }}
]

규칙:
1. image_indices: [순서 블록]에서 IMAGE_N 이 텍스트와 얼마나 가까이 붙어있는지로 판단
2. 제품명: 가능하면 브랜드+모델명. 모르면 설명으로
3. 연예인 이름 불명확하면 제외
4. JSON 배열만 출력 (```json 감싸지 말것)
"""

def build_prompt(fixture):
    title = fixture["title"]
    p = fixture["parsed"]

    # ordered_blocks 사용 (없으면 paragraphs fallback)
    blocks = p.get("ordered_blocks", [])
    if not blocks:
        # fallback: paragraphs만
        for i, para in enumerate(p.get("paragraphs", [])[:50]):
            blocks.append({"type": "text", "content": para})

    # 블록을 번호 붙인 텍스트로 변환
    img_counter = 0
    block_lines = []
    img_url_map = {}  # IMAGE_N → actual url
    for blk in blocks[:120]:
        if blk["type"] == "image":
            label = f"IMAGE_{img_counter}"
            img_url_map[img_counter] = blk["url"]
            block_lines.append(f"[{label}]")
            img_counter += 1
        else:
            t = blk["content"][:100]
            block_lines.append(f"TEXT: {t}")

    block_text = "\n".join(block_lines[:150])

    # 링크 목록
    links = p.get("links", [])
    link_lines = [
        f"  [{lk.get('text','')[:30]}] → {lk.get('resolved_url', lk.get('original_url',''))[:80]}"
        for lk in links[:15]
    ]

    return (
        f"## 제목\n{title}\n\n"
        f"## 순서 블록 (텍스트+이미지 등장 순서)\n{block_text}\n\n"
        f"## 링크 목록\n" + "\n".join(link_lines)
    ), img_url_map


def safe_parse_json(raw: str) -> list:
    """LLM 출력에서 JSON 배열 안전 파싱"""
    # ```json ... ``` 제거
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 배열 부분만 추출 시도
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                return []
        else:
            return []

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def extract_items(fixture, client) -> list:
    prompt, img_url_map = build_prompt(fixture)
    links = fixture["parsed"].get("links", [])

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2500,
    )
    raw = resp.choices[0].message.content.strip()
    items_raw = safe_parse_json(raw)

    results = []
    for item in items_raw:
        # image_indices → actual URLs
        indices = item.get("image_indices", [])
        if not isinstance(indices, list):
            indices = []
        image_urls = [img_url_map[i] for i in indices if isinstance(i, int) and i in img_url_map]

        # 링크 매칭 (link_text 기반)
        link_url = ""
        link_text_key = item.get("link_text", "")
        for lk in links:
            lk_text = lk.get("text", "") if isinstance(lk, dict) else ""
            if link_text_key and link_text_key[:10] in lk_text:
                link_url = lk.get("resolved_url", lk.get("original_url", ""))
                break

        celeb = item.get("celeb", "")
        category = item.get("category", "기타")
        product_name = item.get("product_name", "")
        keywords = item.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []

        if not celeb or not product_name:
            continue

        results.append({
            "celeb":        celeb,
            "category":     category,
            "product_name": product_name,
            "image_urls":   image_urls,
            "keywords":     keywords,
            "link_url":     link_url,
            "source_title": fixture.get("title", ""),
            "source_url":   fixture.get("url", ""),
            "blog_id":      fixture.get("blog_id", ""),
        })

    return results


def main():
    client = get_client()

    fixture_files = sorted(
        f for f in os.listdir(FIXTURES_DIR)
        if f.endswith(".json") and not f.startswith("_")
    )

    all_items = []

    for fname in fixture_files:
        path = os.path.join(FIXTURES_DIR, fname)
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)

        title = fixture.get("title", fname)
        print(f"\n[추출] {title[:55]}")
        try:
            items = extract_items(fixture, client)
            print(f"  → {len(items)}개 아이템")
            for it in items:
                imgs = len(it["image_urls"])
                print(f"    [{it['category']}] {it['celeb']} | {it['product_name'][:40]} | 이미지:{imgs} | {', '.join(it['keywords'][:2])}")
            all_items.extend(items)
        except Exception as e:
            import traceback
            print(f"  오류: {e}")
            traceback.print_exc()

    # 저장
    out_path = os.path.join(OUT_DIR, "celeb_items.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"{'연예인':<10} {'카테고리':<8} {'제품명':<38} {'이미지':<5} {'키워드'}")
    print("-"*80)
    for it in all_items:
        print(f"{it['celeb']:<10} {it['category']:<8} {it['product_name'][:38]:<38} {len(it['image_urls']):<5} {', '.join(it['keywords'][:2])}")

    print(f"\n총 {len(all_items)}개 아이템 → {out_path}")


if __name__ == "__main__":
    main()
