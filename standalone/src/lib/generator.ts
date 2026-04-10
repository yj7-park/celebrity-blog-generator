import OpenAI from "openai";

export async function generateBlogPost(
  celeb: string,
  items: Record<string, string>,
  snippets: string[],
  client: OpenAI
): Promise<string> {
  const itemsText =
    Object.entries(items).length > 0
      ? Object.entries(items)
          .slice(0, 20)
          .map(([k, v]) => `- ${k}: ${v}`)
          .join("\n")
      : "수집된 아이템 없음";

  const contextText = snippets.slice(0, 3).join("\n\n").slice(0, 2000);

  const prompt = `연예인 '${celeb}'에 관한 패션/라이프스타일 블로그 게시글을 작성해주세요.

수집된 아이템 정보:
${itemsText}

참고 블로그 내용:
${contextText || "(없음)"}

다음 형식으로 작성해주세요:
1. SEO 최적화된 제목
2. 흥미로운 도입부 (2-3문장)
3. 주요 아이템 3-5개 각각 상세 소개
4. 마무리 문단
5. 관련 해시태그 10개

독자가 구매 욕구를 느낄 수 있도록 생동감 있게 작성해주세요.`;

  try {
    const res = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: "당신은 연예인 패션과 라이프스타일 아이템을 소개하는 인기 블로거입니다.",
        },
        { role: "user", content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 3000,
    });
    return res.choices[0].message.content ?? "";
  } catch (e) {
    return `블로그 생성 오류: ${e}`;
  }
}
