import { BLOGS } from "./blogs";
import type { OrderedBlock, PostItem, ScrapedPostData } from "./types";

// ── CORS 프록시 (순서대로 fallback) ──────────────────────────────
const PROXIES = [
  (url: string) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}&_=${Date.now()}`,
  (url: string) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
];

async function fetchViaProxy(url: string, timeoutMs = 10000): Promise<string> {
  let lastErr: unknown;
  for (const proxyFn of PROXIES) {
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), timeoutMs);
      const res = await fetch(proxyFn(url), { signal: ctrl.signal });
      clearTimeout(tid);
      if (res.ok) {
        const text = await res.text();
        if (text.length > 100) return text;
      }
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr ?? new Error("All proxies failed");
}

// ── RSS 수집 ──────────────────────────────────────────────────────
function parseRSS(xml: string, folder: string): PostItem[] {
  try {
    const doc = new DOMParser().parseFromString(xml, "application/xml");
    return Array.from(doc.querySelectorAll("item"))
      .filter((el) => el.querySelector("category")?.textContent?.trim() === folder)
      .map((el) => ({
        title: el.querySelector("title")?.textContent ?? "",
        url:   el.querySelector("guid")?.textContent ?? "",
        date:  el.querySelector("pubDate")?.textContent ?? "",
        tag:   el.querySelector("tag")?.textContent ?? "",
      }));
  } catch {
    return [];
  }
}

async function fetchRSS(name: string, folder: string): Promise<PostItem[]> {
  try {
    const xml = await fetchViaProxy(`https://rss.blog.naver.com/${name}.xml`);
    return parseRSS(xml, folder);
  } catch {
    return [];
  }
}

export async function collectPosts(
  days: number,
  onProgress?: (done: number, total: number) => void
): Promise<PostItem[]> {
  const results: PostItem[] = [];
  const CHUNK = 3;

  for (let i = 0; i < BLOGS.length; i += CHUNK) {
    const chunk = BLOGS.slice(i, i + CHUNK);
    const chunkRes = await Promise.all(
      chunk.map(async ([name, folder]) => {
        const posts = await fetchRSS(name, folder);
        onProgress?.(Math.min(i + CHUNK, BLOGS.length), BLOGS.length);
        return posts;
      })
    );
    results.push(...chunkRes.flat());
  }

  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return results
    .filter((p) => {
      const t = new Date(p.date).getTime();
      return !isNaN(t) && t >= cutoff;
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

// ── 블로그 HTML 스크래핑 ──────────────────────────────────────────

/** 네이버 블로그 URL → blogId + logNo 추출 */
function parseNaverUrl(url: string): { blogId: string; logNo: string } | null {
  const m =
    url.match(/blog\.naver\.com\/([^/?#]+)\/(\d+)/) ??
    url.match(/blogId=([^&]+).*logNo=(\d+)/);
  if (!m) return null;
  return { blogId: m[1], logNo: m[2] };
}

function buildPostViewUrl(blogId: string, logNo: string): string {
  return `https://blog.naver.com/PostView.naver?blogId=${blogId}&logNo=${logNo}&redirect=Dlog&widgetTypeCall=true&directAccess=false`;
}

function parseNaverHtml(html: string, sourceTitle: string, sourceUrl: string): ScrapedPostData {
  const doc = new DOMParser().parseFromString(html, "text/html");

  // ── 이미지 URL (원본 해상도) ──
  const imageUrls: string[] = [];
  const seenImgs = new Set<string>();
  doc.querySelectorAll("img.se-image-resource, img[src*='postfiles.pstatic.net']").forEach((img) => {
    let src = img.getAttribute("src") || img.getAttribute("data-lazy-src") || "";
    if (src && src.includes("pstatic.net")) {
      src = src.replace(/\?type=\w+/, "?type=w966");
      if (!seenImgs.has(src)) { seenImgs.add(src); imageUrls.push(src); }
    }
  });

  // ── 텍스트 단락 ──
  const paragraphs: string[] = [];
  doc.querySelectorAll("p.se-text-paragraph").forEach((p) => {
    const t = p.textContent?.replace(/\u200b/g, "").replace(/\xa0/g, " ").trim() ?? "";
    if (t) paragraphs.push(t);
  });

  // ── ordered_blocks (텍스트+이미지 순서 보존) ──
  const orderedBlocks: OrderedBlock[] = [];
  const container = doc.querySelector("div.se-main-container, div.__se_component_area");
  if (container) {
    const walk = (node: Element) => {
      if (node.matches("p.se-text-paragraph")) {
        const t = node.textContent?.replace(/\u200b/g, "").replace(/\xa0/g, " ").trim() ?? "";
        if (t) orderedBlocks.push({ type: "text", content: t });
      } else if (node.matches("img.se-image-resource, img[src*='postfiles.pstatic.net']")) {
        let src = node.getAttribute("src") || node.getAttribute("data-lazy-src") || "";
        if (src && src.includes("pstatic.net")) {
          src = src.replace(/\?type=\w+/, "?type=w966");
          orderedBlocks.push({ type: "image", url: src });
        }
      } else {
        Array.from(node.children).forEach(walk);
      }
    };
    Array.from(container.children).forEach(walk);
  }

  // ── 링크 ──
  const links: Array<{ text: string; href: string }> = [];
  doc.querySelectorAll("a.se-link, a[href*='coupang'], a[href*='smartstore'], a[href*='vvd.bz']").forEach((a) => {
    const href = a.getAttribute("href") || "";
    const text = a.textContent?.trim() ?? "";
    if (href.startsWith("http")) links.push({ text, href });
  });

  return { orderedBlocks, imageUrls, paragraphs, links, postUrl: sourceUrl, title: sourceTitle };
}

export async function scrapePost(post: PostItem): Promise<ScrapedPostData | null> {
  try {
    const parsed = parseNaverUrl(post.url);
    if (!parsed) return null;
    const pvUrl = buildPostViewUrl(parsed.blogId, parsed.logNo);
    const html = await fetchViaProxy(pvUrl, 12000);
    return parseNaverHtml(html, post.title, post.url);
  } catch {
    return null;
  }
}

export async function scrapeMultiplePosts(
  posts: PostItem[],
  maxPosts = 8,
  onProgress?: (done: number, total: number) => void
): Promise<ScrapedPostData[]> {
  const targets = posts.slice(0, maxPosts);
  const results: ScrapedPostData[] = [];

  for (let i = 0; i < targets.length; i++) {
    const data = await scrapePost(targets[i]);
    if (data && (data.paragraphs.length > 0 || data.imageUrls.length > 0)) {
      results.push(data);
    }
    onProgress?.(i + 1, targets.length);
  }

  return results;
}
