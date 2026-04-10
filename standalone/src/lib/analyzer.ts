import OpenAI from "openai";
import type { PostItem } from "./collector";

export function createClient(apiKey: string): OpenAI {
  return new OpenAI({ apiKey, dangerouslyAllowBrowser: true });
}

export async function extractCeleb(title: string, client: OpenAI): Promise<string> {
  try {
    const res = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content:
            "문구를 입력하면 그 문구로부터 연예인의 이름을 찾아서 출력해줘. " +
            "문장이 나와도 문장에 대답하지 말고, 해당 문장에 등장하는 연예인의 이름만 찾아서 출력해. " +
            "여러 명이면 쉼표로 구분해. 연예인이 없으면 빈 문자열만 출력해.",
        },
        { role: "user", content: "이달의소녀덤덤이달의소녀 롤링다이스로 롤아웃 풀세트 연봄빛 코드" },
        { role: "assistant", content: "이달의소녀" },
        { role: "user", content: "이도경5이도경이봉지아 1회 이도경의 봄 봄트 착용 의상" },
        { role: "assistant", content: "이도경, 봉지아" },
        { role: "user", content: "이재호 혼자사는 이민호 집 거실 뭐가있나요?" },
        { role: "assistant", content: "이재호" },
        { role: "user", content: title },
      ],
      temperature: 1,
      max_tokens: 100,
    });
    return res.choices[0].message.content?.trim() ?? "";
  } catch {
    return "";
  }
}

export async function getTrendingCelebs(
  posts: PostItem[],
  client: OpenAI,
  topN = 3,
  onProgress?: (done: number, total: number) => void
): Promise<string[]> {
  const counts = new Map<string, number>();

  for (let i = 0; i < posts.length; i++) {
    const result = await extractCeleb(posts[i].title, client);
    result
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean)
      .forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1));
    onProgress?.(i + 1, posts.length);
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([name]) => name);
}
