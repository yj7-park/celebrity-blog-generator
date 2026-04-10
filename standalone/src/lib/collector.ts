import { BLOGS } from "./blogs";

export interface PostItem {
  title: string;
  url: string;
  date: string;
  tag: string;
}

// Public CORS proxy — requests Naver RSS/HTML on behalf of the browser
const PROXY = "https://api.allorigins.win/raw?url=";

function proxied(url: string): string {
  return `${PROXY}${encodeURIComponent(url)}`;
}

function parseRSS(xml: string, folder: string): PostItem[] {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const items = Array.from(doc.querySelectorAll("item"));
  return items
    .filter((el) => el.querySelector("category")?.textContent?.trim() === folder)
    .map((el) => ({
      title: el.querySelector("title")?.textContent ?? "",
      url: el.querySelector("guid")?.textContent ?? "",
      date: el.querySelector("pubDate")?.textContent ?? "",
      tag: el.querySelector("tag")?.textContent ?? "",
    }));
}

async function fetchRSS(name: string, folder: string): Promise<PostItem[]> {
  try {
    const url = `https://rss.blog.naver.com/${name}.xml`;
    const res = await fetch(proxied(url));
    if (!res.ok) return [];
    return parseRSS(await res.text(), folder);
  } catch {
    return [];
  }
}

export async function collectPosts(
  days: number,
  onProgress?: (done: number, total: number) => void
): Promise<PostItem[]> {
  const results: PostItem[] = [];
  for (let i = 0; i < BLOGS.length; i++) {
    const [name, folder] = BLOGS[i];
    const posts = await fetchRSS(name, folder);
    results.push(...posts);
    onProgress?.(i + 1, BLOGS.length);
  }

  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return results
    .filter((p) => {
      const t = new Date(p.date).getTime();
      return !isNaN(t) && t >= cutoff;
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

// ── Blog post HTML scraping ──────────────────────────────────────

function extractNaverContentUrl(html: string): string | null {
  // Naver wraps posts in a frame; the real content URL is in a src attribute
  const match = html.match(/src="(\/[^"]+PostView[^"]+)"/);
  return match ? `https://blog.naver.com${match[1]}` : null;
}

function parseContent(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const paras = Array.from(doc.querySelectorAll("p.se-text-paragraph"));
  return paras
    .map((p) => p.textContent ?? "")
    .join("\n")
    .replace(/\u200b/g, "")
    .trim();
}

function parseItems(html: string): Record<string, string> {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const result: Record<string, string> = {};
  doc.querySelectorAll("a.se-link").forEach((a) => {
    const href = (a as HTMLAnchorElement).href || a.getAttribute("href") || "";
    const text = a.textContent?.trim() ?? "";
    if (!href || !text) return;
    // Try to extract product name from URL params (works without redirect)
    const name = parseItemName(href);
    if (name) result[text] = name;
  });
  return result;
}

function parseItemName(url: string): string {
  try {
    const u = new URL(url);
    return (
      decodeURIComponent(u.searchParams.get("q") ?? "") ||
      decodeURIComponent(u.searchParams.get("pageKey") ?? "")
    );
  } catch {
    return "";
  }
}

export interface ScrapedPost {
  content: string;
  items: Record<string, string>;
}

export async function scrapePost(url: string): Promise<ScrapedPost> {
  try {
    const frameHtml = await fetch(proxied(url)).then((r) => r.text());
    const contentUrl = extractNaverContentUrl(frameHtml) ?? url;
    const html = await fetch(proxied(contentUrl)).then((r) => r.text());
    return { content: parseContent(html), items: parseItems(html) };
  } catch {
    return { content: "", items: {} };
  }
}

export async function scrapePostsForCeleb(
  posts: PostItem[],
  celeb: string,
  maxPosts = 5,
  onProgress?: (done: number, total: number) => void
): Promise<{ items: Record<string, string>; snippets: string[] }> {
  const celebPosts = posts
    .filter((p) => p.title.includes(celeb))
    .slice(0, maxPosts);

  const allItems: Record<string, string> = {};
  const snippets: string[] = [];

  for (let i = 0; i < celebPosts.length; i++) {
    const { content, items } = await scrapePost(celebPosts[i].url);
    if (content) snippets.push(content.slice(0, 500));
    Object.assign(allItems, items);
    onProgress?.(i + 1, celebPosts.length);
  }

  return { items: allItems, snippets };
}
