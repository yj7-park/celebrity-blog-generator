import type OpenAI from "openai";
import type { CelebItem, ScrapedPostData } from "./types";

const CATEGORY_GUIDE = `
카테고리 기준:
가방(핸드백/숄더백/백팩/클러치), 신발(스니커즈/플랫/힐/부츠/샌들),
의류(코트/자켓/가디건/니트/셔츠/원피스/팬츠 등),
뷰티(스킨케어/메이크업/향수/헤어), 식품(음식/영양제/음료),
생활(주방/청소/가전/인테리어), 액세서리(주얼리/시계/선글라스/벨트), 기타
`;

const SYSTEM_PROMPT = `당신은 연예인 협찬·착용 아이템 정보를 블로그에서 구조화 추출하는 전문가입니다.

블로그 포스트의 순서 블록(TEXT/IMAGE_N이 등장 순서대로 나열)을 분석하여
각 연예인이 착용·사용한 아이템을 JSON 배열로 추출하세요.

${CATEGORY_GUIDE}

출력 형식 (순수 JSON 배열):
[
  {
    "celeb": "연예인 이름",
    "category": "카테고리",
    "product_name": "브랜드명 + 제품명 (최대한 구체적으로)",
    "image_indices": [0, 2],
    "keywords": ["방송명/회차", "키워드"],
    "link_text": "▶...보러가기 형태 텍스트"
  }
]

규칙:
1. image_indices: IMAGE_N 레이블 중 해당 제품과 가장 가까이 있는 인덱스
2. 제품명: 브랜드+모델명 포함, 모르면 텍스트 설명으로
3. 연예인 이름 불명확하면 제외
4. JSON 배열만 출력 (마크다운 코드블록 없이)`;

function buildPrompt(scraped: ScrapedPostData): { prompt: string; imgMap: Map<number, string> } {
  const imgMap = new Map<number, string>();
  let imgCounter = 0;
  const blockLines: string[] = [];

  for (const blk of scraped.orderedBlocks.slice(0, 120)) {
    if (blk.type === "image" && blk.url) {
      imgMap.set(imgCounter, blk.url);
      blockLines.push(`[IMAGE_${imgCounter}]`);
      imgCounter++;
    } else if (blk.type === "text" && blk.content) {
      blockLines.push(`TEXT: ${blk.content.slice(0, 100)}`);
    }
  }

  // ordered_blocks가 없으면 paragraphs + imageUrls fallback
  if (imgCounter === 0 && scraped.imageUrls.length > 0) {
    scraped.imageUrls.forEach((url, i) => imgMap.set(i, url));
    scraped.paragraphs.slice(0, 40).forEach((p) => blockLines.push(`TEXT: ${p.slice(0, 100)}`));
    scraped.imageUrls.forEach((_, i) => blockLines.push(`[IMAGE_${i}]`));
  }

  const linkLines = scraped.links
    .slice(0, 10)
    .map((lk) => `  [${lk.text.slice(0, 25)}] → ${lk.href.slice(0, 60)}`);

  const prompt =
    `## 제목\n${scraped.title}\n\n` +
    `## 순서 블록\n${blockLines.join("\n")}\n\n` +
    `## 링크\n${linkLines.join("\n")}`;

  return { prompt, imgMap };
}

function safeParseJson(raw: string): Array<Record<string, unknown>> {
  const cleaned = raw.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
  try {
    const parsed = JSON.parse(cleaned);
    if (Array.isArray(parsed)) return parsed.filter((x) => typeof x === "object" && x !== null);
    if (typeof parsed === "object") {
      for (const v of Object.values(parsed)) {
        if (Array.isArray(v)) return v.filter((x) => typeof x === "object" && x !== null);
      }
    }
  } catch {
    const m = cleaned.match(/\[[\s\S]*\]/);
    if (m) {
      try {
        const arr = JSON.parse(m[0]);
        if (Array.isArray(arr)) return arr.filter((x) => typeof x === "object" && x !== null);
      } catch { /* ignore */ }
    }
  }
  return [];
}

async function extractFromPost(scraped: ScrapedPostData, client: OpenAI): Promise<CelebItem[]> {
  const { prompt, imgMap } = buildPrompt(scraped);

  const resp = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user",   content: prompt },
    ],
    temperature: 0.1,
    max_tokens: 2000,
  });

  const raw = resp.choices[0].message.content ?? "";
  const items = safeParseJson(raw);

  return items
    .map((item) => {
      const indices: number[] = Array.isArray(item.image_indices)
        ? (item.image_indices as unknown[]).filter((i): i is number => typeof i === "number")
        : [];
      const imageUrls = indices.map((i) => imgMap.get(i)).filter((u): u is string => !!u);

      // 링크 매칭
      const linkText = String(item.link_text ?? "");
      const matchedLink = scraped.links.find((lk) =>
        linkText && lk.text.includes(linkText.slice(0, 8))
      );

      const celeb       = String(item.celeb ?? "").trim();
      const productName = String(item.product_name ?? "").trim();
      if (!celeb || !productName) return null;

      const keywords = Array.isArray(item.keywords)
        ? (item.keywords as unknown[]).map(String)
        : [];

      return {
        celeb,
        category:     String(item.category ?? "기타"),
        product_name: productName,
        image_urls:   imageUrls,
        keywords,
        link_url:     matchedLink?.href ?? "",
        source_title: scraped.title,
        source_url:   scraped.postUrl,
      } satisfies CelebItem;
    })
    .filter((x): x is CelebItem => x !== null);
}

export async function extractItemsFromPosts(
  scrapedPosts: ScrapedPostData[],
  client: OpenAI,
  onProgress?: (done: number, total: number) => void
): Promise<CelebItem[]> {
  const all: CelebItem[] = [];

  for (let i = 0; i < scrapedPosts.length; i++) {
    try {
      const items = await extractFromPost(scrapedPosts[i], client);
      all.push(...items);
    } catch {
      /* 개별 실패는 무시하고 계속 */
    }
    onProgress?.(i + 1, scrapedPosts.length);
  }

  // 중복 제거 (같은 celeb + product_name)
  const seen = new Set<string>();
  return all.filter((item) => {
    const key = `${item.celeb}::${item.product_name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
