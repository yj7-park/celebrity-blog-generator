import type OpenAI from "openai";
import type { CelebItem } from "./types";

export async function generateBlogPost(
  celebItems: CelebItem[],
  client: OpenAI
): Promise<string> {
  if (celebItems.length === 0) return "생성할 아이템 정보가 없습니다.";

  // 연예인별 그룹화
  const grouped = new Map<string, CelebItem[]>();
  for (const item of celebItems) {
    if (!grouped.has(item.celeb)) grouped.set(item.celeb, []);
    grouped.get(item.celeb)!.push(item);
  }

  // 가장 아이템이 많은 연예인을 대표로
  const [mainCeleb, mainItems] = [...grouped.entries()].sort(
    (a, b) => b[1].length - a[1].length
  )[0];

  const itemsText = mainItems
    .slice(0, 10)
    .map((it) => `- [${it.category}] ${it.product_name} (키워드: ${it.keywords.join(", ")})`)
    .join("\n");

  const prompt = `연예인 '${mainCeleb}'의 착용·사용 아이템에 관한 블로그 포스트를 작성해주세요.

수집된 아이템:
${itemsText}

형식:
1. SEO 최적화 제목
2. 흥미로운 도입부 (2~3문장)
3. 아이템별 상세 소개 (각 아이템마다 카테고리·특징 포함)
4. 마무리 문단
5. 해시태그 10개

독자가 구매 욕구를 느낄 수 있도록 생동감 있게 작성해주세요.`;

  try {
    const resp = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: "당신은 연예인 패션과 라이프스타일 아이템을 소개하는 인기 블로거입니다." },
        { role: "user", content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 3000,
    });
    return resp.choices[0].message.content ?? "";
  } catch (e) {
    return `블로그 생성 오류: ${e}`;
  }
}
