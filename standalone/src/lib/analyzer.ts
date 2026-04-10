import OpenAI from "openai";
import type { PostItem } from "./types";

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
  topN = 5,
  onProgress?: (done: number, total: number) => void
): Promise<string[]> {
  if (posts.length === 0) return [];

  // Batch analysis to save costs and time
  const titlesBlock = posts.map((p, i) => `${i + 1}. ${p.title}`).join("\n");
  
  onProgress?.(30, 100); // Started
  
  try {
    // Support testing with dummy key
    if (client.apiKey === "dummy-key") {
      await new Promise((r) => setTimeout(r, 1000));
      onProgress?.(100, 100);
      return ["윤은혜", "최화정", "한가인", "차정원", "심우명"];
    }

    const res = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content:
            "당신은 연예 트렌드 분석 전문가입니다. 제공된 블로그 게시글 제목 목록을 분석하여 " +
            "현재 가장 많이 언급되거나 화제가 되고 있는 연예인(셀럽)들을 추출하세요.\n" +
            "규칙:\n" +
            "1. 제목에서 옷, 가방, 액세서리 정보가 포함된 연예인을 우선순위로 두세요.\n" +
            "2. 상위 연예인들의 이름을 중요도 순으로 나열하세요.\n" +
            "3. 이름만 쉼표(,)로 구분하여 정확히 출력하세요. 부가 설명은 생략하세요.",
        },
        { role: "user", content: `분석할 제목 목록:\n${titlesBlock}` },
      ],
      temperature: 0.3, // Lower temperature for more consistent results
    });

    onProgress?.(90, 100);
    
    const content = res.choices[0].message.content?.trim() ?? "";
    const celebs = content
      .split(/[,|\n]/) // Split by comma or newline just in case
      .map((c) => c.replace(/^\d+\.\s*/, "").trim()) // Remove leading numbers if LLM ignored instructions
      .filter((c) => c.length > 1 && c.length < 10) // Filter out noise
      .filter((c, i, self) => self.indexOf(c) === i); // Unique

    onProgress?.(100, 100);
    return celebs.slice(0, topN);
  } catch (e) {
    console.error("Analysis failed:", e);
    return [];
  }
}
