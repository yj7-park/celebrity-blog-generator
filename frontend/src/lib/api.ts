import type {
  PostItem,
  CelebItem,
  CelebItemRecord,
  ScrapedPostRecord,
  CoupangProduct,
  ScheduleJob,
  AppSettings,
  PipelineEvent,
  PipelineRun,
  CheckRunResponse,
} from "./types";

export const BASE_URL = "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

// --- Pipeline ---
export async function collectPosts(days: number): Promise<{ posts: PostItem[]; count: number }> {
  return apiFetch("/api/pipeline/collect", {
    method: "POST",
    body: JSON.stringify({ days }),
  });
}

export async function analyzeCelebs(
  posts: PostItem[],
  apiKey: string,
  topN = 3
): Promise<{ trending: string[]; post_count: number }> {
  return apiFetch("/api/pipeline/analyze", {
    method: "POST",
    body: JSON.stringify({ posts, openai_api_key: apiKey, top_n: topN }),
  });
}

export async function scrapePosts(
  posts: PostItem[],
  celeb: string,
  maxPosts = 10
): Promise<{ celeb: string; items: CelebItem[] }> {
  return apiFetch("/api/pipeline/scrape", {
    method: "POST",
    body: JSON.stringify({ posts, celeb, max_posts: maxPosts }),
  });
}

export async function generatePost(
  items: CelebItem[],
  apiKey: string
): Promise<{ celeb: string; blog_post: string }> {
  return apiFetch("/api/pipeline/generate", {
    method: "POST",
    body: JSON.stringify({ items, openai_api_key: apiKey }),
  });
}

// --- Coupang ---
export async function searchCoupang(
  keyword: string,
  limit = 10
): Promise<{ products: CoupangProduct[] }> {
  return apiFetch("/api/coupang/search", {
    method: "POST",
    body: JSON.stringify({ keyword, limit }),
  });
}

export async function getAffiliateUrl(productUrl: string): Promise<{ affiliate_url: string }> {
  return apiFetch(`/api/coupang/affiliate?product_url=${encodeURIComponent(productUrl)}`);
}

export async function shortenUrl(url: string): Promise<{ short_url: string }> {
  return apiFetch("/api/coupang/shorten", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

// --- Naver Blog ---
export async function writeNaverBlog(
  title: string,
  elements: { type: string; content: string }[],
  tags: string[],
  thumbnailPath?: string
): Promise<{ success: boolean; blog_url?: string; error?: string }> {
  return apiFetch("/api/naver/write", {
    method: "POST",
    body: JSON.stringify({ title, elements, tags, thumbnail_path: thumbnailPath }),
  });
}

export async function getNaverStatus(): Promise<{ status: string; url?: string; error?: string }> {
  return apiFetch("/api/naver/status");
}

// --- Scheduler ---
export async function getSchedulerJobs(): Promise<{ jobs: ScheduleJob[] }> {
  return apiFetch("/api/scheduler/jobs");
}

export async function createSchedulerJob(
  job: Omit<ScheduleJob, "id" | "last_run" | "next_run">
): Promise<ScheduleJob> {
  return apiFetch("/api/scheduler/jobs", {
    method: "POST",
    body: JSON.stringify(job),
  });
}

export async function updateSchedulerJob(
  id: string,
  job: Partial<ScheduleJob>
): Promise<ScheduleJob> {
  return apiFetch(`/api/scheduler/jobs/${id}`, {
    method: "PUT",
    body: JSON.stringify(job),
  });
}

export async function deleteSchedulerJob(id: string): Promise<void> {
  await apiFetch(`/api/scheduler/jobs/${id}`, { method: "DELETE" });
}

export async function triggerSchedulerJob(id: string): Promise<{ status: string }> {
  return apiFetch(`/api/scheduler/jobs/${id}/run`, { method: "POST" });
}

// --- Settings ---
export async function getSettings(): Promise<AppSettings> {
  return apiFetch("/api/settings");
}

export async function saveSettings(settings: AppSettings): Promise<{ status: string }> {
  return apiFetch("/api/settings", {
    method: "POST",
    body: JSON.stringify(settings),
  });
}

// --- DB / History ---
export async function checkRecentRun(celeb: string, days = 7): Promise<CheckRunResponse> {
  return apiFetch(`/api/db/check?celeb=${encodeURIComponent(celeb)}&days=${days}`);
}

export async function listRuns(): Promise<{ runs: PipelineRun[] }> {
  return apiFetch("/api/db/runs");
}

export async function getRun(id: string): Promise<PipelineRun> {
  return apiFetch(`/api/db/runs/${id}`);
}

export async function deleteRun(id: string): Promise<void> {
  await apiFetch(`/api/db/runs/${id}`, { method: "DELETE" });
}

// --- Celeb Items ---
export async function listCelebItems(celeb = "", limit = 500): Promise<{ items: CelebItemRecord[] }> {
  const qs = celeb ? `?celeb=${encodeURIComponent(celeb)}&limit=${limit}` : `?limit=${limit}`;
  return apiFetch(`/api/db/celeb-items${qs}`);
}

export async function deleteCelebItem(id: string): Promise<void> {
  await apiFetch(`/api/db/celeb-items/${id}`, { method: "DELETE" });
}

export async function deleteCelebItemsByPost(postUrl: string): Promise<{ deleted: number }> {
  return apiFetch(`/api/db/celeb-items-by-post?post_url=${encodeURIComponent(postUrl)}`, {
    method: "DELETE",
  });
}

// --- Scraped Post Cache ---
export async function listScrapedPosts(): Promise<{ posts: ScrapedPostRecord[] }> {
  return apiFetch("/api/db/scraped-posts");
}

export async function deleteScrapedPost(id: string): Promise<void> {
  await apiFetch(`/api/db/scraped-posts/${id}`, { method: "DELETE" });
}

// --- SSE Pipeline ---
export interface RunPipelineParams {
  days: number;
  max_posts: number;
  top_celebs: number;
  openai_api_key: string;
}

export function runPipelineSSE(
  params: RunPipelineParams,
  onEvent: (event: PipelineEvent) => void,
  onError: (err: string) => void
): EventSource {
  const qs = new URLSearchParams({
    days: String(params.days),
    max_posts: String(params.max_posts),
    top_celebs: String(params.top_celebs),
    openai_api_key: params.openai_api_key,
  });
  const url = `${BASE_URL}/api/pipeline/run?${qs.toString()}`;
  const es = new EventSource(url);

  es.onmessage = (e) => {
    try {
      const event: PipelineEvent = JSON.parse(e.data);
      onEvent(event);
      if (event.type === "done" || event.type === "error") es.close();
    } catch {
      // parse error 무시
    }
  };

  es.onerror = () => {
    onError("서버 연결 오류가 발생했습니다.");
    es.close();
  };

  return es;
}
