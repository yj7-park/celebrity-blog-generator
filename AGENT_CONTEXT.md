# WS2 Project — Agent Context

> Last updated: 2026-04-10  
> Purpose: Quick-start reference for any agent continuing this project.

---

## 1. Project Overview

**Goal**: Collect Korean celebrity fashion/lifestyle items from Naver blogs and auto-generate SEO blog posts.

**Pipeline**:
1. Collect RSS posts from curated Naver bloggers
2. Identify trending celebrities (GPT-4o-mini batch analysis)
3. Scrape full HTML from each Naver blog post (via CORS proxy)
4. Use GPT-4o-mini to extract structured items: `celeb × category × product_name × image_urls × keywords × link_url`
5. Generate an SEO-optimized Korean blog post from the extracted items

---

## 2. Repo Structure

```
ws2/
├── .env                         # gh_token, openai_token, hf_token
├── .github/workflows/deploy.yml # GitHub Actions: main → web branch (GitHub Pages)
├── AGENT_CONTEXT.md             # ← this file
│
├── standalone/                  # Pure client-side Vite+React+TS app (GitHub Pages)
│   ├── src/
│   │   ├── App.tsx              # API key input, days selector, mode toggle
│   │   ├── lib/
│   │   │   ├── types.ts         # Shared interfaces: PostItem, ScrapedPostData, CelebItem
│   │   │   ├── blogs.ts         # 15 Naver blog IDs + category folders
│   │   │   ├── collector.ts     # RSS collect + HTML scraping via CORS proxy
│   │   │   ├── extractor.ts     # LLM-based structured item extraction
│   │   │   ├── generator.ts     # Blog post generation from CelebItem[]
│   │   │   └── analyzer.ts      # Celebrity name extraction + trending analysis
│   │   └── components/
│   │       ├── AutoMode.tsx     # One-button full pipeline
│   │       ├── StepMode.tsx     # Step-by-step with intermediate state views
│   │       ├── ItemsPanel.tsx   # Displays CelebItem[] as rich table with images
│   │       ├── TrendingPanel.tsx# Celeb selector
│   │       ├── PostsPanel.tsx   # RSS posts list
│   │       ├── BlogPostPanel.tsx# Generated post with copy button
│   │       ├── StepCard.tsx     # Step container (idle/running/done/error)
│   │       ├── ProgressBar.tsx  # Progress indicator
│   │       ├── ModeToggle.tsx   # Auto / Step-by-step toggle
│   │       └── Card.tsx         # Base card UI
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                     # FastAPI server (not deployed; local dev only)
│   ├── main.py                  # CORS + static serving + SSE pipeline endpoint
│   ├── routers/blog.py          # REST + SSE endpoints
│   ├── services/
│   │   ├── collector.py
│   │   ├── analyzer.py
│   │   └── generator.py
│   └── models/schemas.py
│
└── pipeline/                    # Python scripts for offline data exploration
    ├── collect_fixtures.py      # Scrapes Naver blog HTML → saves JSON fixtures
    ├── extract_items.py         # Runs LLM extraction on fixtures → celeb_items.json
    ├── fixtures/                # Per-blog scraped HTML data (JSON)
    └── extracted/celeb_items.json  # Aggregated structured items output
```

---

## 3. Key Technical Details

### Naver Blog URL Pattern
- RSS: `https://rss.blog.naver.com/{blogId}.xml`  (filter by `<category>` == folder)
- Actual content URL: `https://blog.naver.com/PostView.naver?blogId={id}&logNo={no}&redirect=Dlog&widgetTypeCall=true&directAccess=false`
- Outer page is a frameset (useless); PostView URL gives the real Smart Editor 4 HTML

### CORS Proxies (browser-side)
```
https://api.allorigins.win/raw?url=ENCODED_URL&_=TIMESTAMP  (primary)
https://corsproxy.io/?ENCODED_URL                           (fallback)
```
Both tried in order; 10-second timeout per proxy.

### HTML Parsing Selectors (Smart Editor 4)
- Text paragraphs: `p.se-text-paragraph`
- Images: `img.se-image-resource`, `img[src*='postfiles.pstatic.net']`
- Links: `a.se-link, a[href*='coupang'], a[href*='smartstore'], a[href*='vvd.bz']`
- Container: `div.se-main-container` or `div.__se_component_area`

### Image URL Resolution
Replace `?type=XXX` → `?type=w966` for full resolution.

### ordered_blocks — Core Concept
DOM is traversed in order, producing an interleaved array of `{type:"text"|"image", content?:string, url?:string}`. This is sent to the LLM as:
```
[IMAGE_0]
TEXT: 아이유가 착용한 가방은...
[IMAGE_1]
TEXT: 롱샴 르 플리아쥬 XL백...
```
LLM returns `image_indices: [0, 1]` which are resolved to actual pstatic.net URLs.

### LLM Usage
- Model: `gpt-4o-mini` for all tasks (extraction, analysis, generation)
- `dangerouslyAllowBrowser: true` required in OpenAI JS SDK for browser use
- Extraction: temperature 0.1, max_tokens 2000
- Generation: temperature 0.8, max_tokens 3000

### CelebItem Interface
```typescript
interface CelebItem {
  celeb: string;           // e.g. "아이유"
  category: string;        // 가방/신발/의류/뷰티/식품/생활/액세서리/기타
  product_name: string;    // brand + model name
  image_urls: string[];    // pstatic.net URLs
  keywords: string[];      // show name, episode, etc.
  link_url: string;        // Coupang / smartstore / vvd.bz
  source_title: string;
  source_url: string;
}
```

---

## 4. GitHub Deployment

- **Branch**: `web` (auto-deployed by GitHub Actions)
- **Trigger**: push to `main` when `standalone/**` changes
- **Workflow**: `.github/workflows/deploy.yml`
  - Node 20, `npm ci`, `npm run build` in `standalone/`
  - `peaceiris/actions-gh-pages@v4` → deploys `standalone/dist` to `web` branch
- **GitHub Pages**: serves the `web` branch

To push and trigger deploy:
```bash
git add standalone/ .github/
git commit -m "your message"
git push origin main
```

---

## 5. Environment Variables

File: `ws2/.env`
```
gh_token=ghp_...          # GitHub PAT with repo + workflow scope
openai_token=sk-proj-...  # OpenAI API key
hf_token=hf_...           # HuggingFace token (unused in current deploy)
```

**The OpenAI key is entered by the user at runtime in the browser UI** — it is never stored in the source code or environment.

---

## 6. Pipeline Flow (Standalone)

```
User enters API key + days
         ↓
collectPosts(days)          → PostItem[]      (RSS from 15 blogs, filtered by date)
         ↓
getTrendingCelebs(posts)    → string[]        (batch LLM analysis of all titles)
         ↓
[User selects celeb in StepMode, or auto picks top-1 in AutoMode]
         ↓
scrapeMultiplePosts(posts)  → ScrapedPostData[] (filter by celeb name in title → scrape HTML)
         ↓
extractItemsFromPosts(scraped) → CelebItem[]  (LLM extraction per post, deduped)
         ↓
generateBlogPost(items)     → string          (Korean SEO blog post)
```

---

## 7. Pending / Future Work

- **Image display**: `ItemsPanel` shows first image; CORS restrictions may block pstatic.net images in browser — consider a proxy or server-side image fetch
- **Celeb filter accuracy**: Currently filters posts where `title.includes(celeb)`; could improve with fuzzy matching
- **More bloggers**: Add to `standalone/src/lib/blogs.ts` — format is `[blogId, categoryFolder]`
- **Short URL resolution**: `vvd.bz` affiliate links need server-side resolution (can't do HEAD request from browser due to CORS); currently stored as-is
- **Backend SSE pipeline**: `backend/` has a streaming FastAPI endpoint (`GET /api/pipeline`) for local use with full short-URL resolution and no CORS limitations
- **Python pipeline scripts**: `pipeline/collect_fixtures.py` + `extract_items.py` for offline batch processing / testing LLM prompts

---

## 8. Running Locally

```bash
# Dev server
cd standalone
npm install
npm run dev   # → http://localhost:5173

# Production build
npm run build  # → standalone/dist/

# Python pipeline (optional)
cd pipeline
pip install openai requests beautifulsoup4
python collect_fixtures.py   # scrapes fixtures/
python extract_items.py      # → extracted/celeb_items.json
```
