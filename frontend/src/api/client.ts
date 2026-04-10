export interface PostItem {
  title: string;
  url: string;
  date: string;
  tag: string;
}

export interface CollectResponse {
  posts: PostItem[];
  count: number;
}

export interface AnalyzeResponse {
  trending: string[];
  post_count: number;
}

export interface ItemsResponse {
  celeb: string;
  items: Record<string, string>;
  content_snippets: string[];
}

export interface GenerateResponse {
  celeb: string;
  blog_post: string;
}

// SSE event payloads
export type PipelineEvent =
  | { type: "progress"; step: string; percent: number }
  | { type: "posts"; data: { count: number; titles: string[] } }
  | { type: "trending"; data: { celebs: string[] } }
  | { type: "items"; data: { items: Record<string, string> } }
  | { type: "blog_post"; data: { celeb: string; post: string } }
  | { type: "error"; message: string }
  | { type: "done" };

// VITE_API_BASE_URL can be set as a GitHub Actions variable (e.g. https://your-backend.com)
const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api`;

export async function collectPosts(days: number): Promise<CollectResponse> {
  const res = await fetch(`${BASE}/collect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ days }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function analyzePosts(
  posts: PostItem[],
  openaiApiKey: string,
  topN = 3
): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ posts, openai_api_key: openaiApiKey, top_n: topN }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchItems(
  posts: PostItem[],
  celeb: string
): Promise<ItemsResponse> {
  const res = await fetch(`${BASE}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ posts, celeb }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generatePost(
  celeb: string,
  items: Record<string, string>,
  contentSnippets: string[],
  openaiApiKey: string
): Promise<GenerateResponse> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      celeb,
      items,
      content_snippets: contentSnippets,
      openai_api_key: openaiApiKey,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function startPipeline(
  days: number,
  openaiApiKey: string,
  onEvent: (event: PipelineEvent) => void,
  onError: (err: string) => void
): EventSource {
  const url = `${BASE}/pipeline?days=${days}&openai_api_key=${encodeURIComponent(openaiApiKey)}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    try {
      const event: PipelineEvent = JSON.parse(e.data);
      onEvent(event);
      if (event.type === "done" || event.type === "error") es.close();
    } catch {
      // ignore parse errors
    }
  };
  es.onerror = () => {
    onError("서버 연결 오류");
    es.close();
  };
  return es;
}
