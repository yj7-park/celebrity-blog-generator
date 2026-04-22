"""
Product image search + multi-source clean reconstruction.

Strategy
--------
1. Build search query: celeb + product_name + keyword-tags (# stripped)
2. Naver BLOG search API (if keys set) — returns up to 100 blog posts per query;
   each post is scraped for product images.  Blog posts from different blogs use
   the same base product photo with different watermark positions → ideal for
   median composite removal.
3. Naver IMAGE search (Selenium fallback) — proven to work; returns clean product
   photos from shopping sites (no watermarks) and blog CDN images.
4. Download candidates → filter by phash similarity to the original
5. Reconstruct a clean image from the collected copies:
     - 3+ copies: pixel-wise median (watermarks are statistical outliers)
     - 2  copies: fill watermarked pixels from the cleaner source
     - 1  copy:   return that image directly if phash diff ≤ 6
6. Side-effect: blog post URLs → register new blogs in blog_sources (inactive).
"""
from __future__ import annotations

import io
import logging
import re
import time
import warnings
from typing import Optional
from urllib.parse import quote, urlparse, parse_qs

import requests
from PIL import Image

DOWNLOAD_TIMEOUT = 8
SIMILAR_THRESHOLD = 30   # phash distance — "similar product" threshold (broader)
SAME_PHOTO_THRESHOLD = 10  # phash distance — same base photo (different watermark)
DIRECT_THRESHOLD  = 6    # phash distance — treat as near-identical copy


# ── Query builder ─────────────────────────────────────────────────────────────

def build_search_query(celeb: str, product_name: str, keywords: list[str]) -> str:
    """
    "아이유 화이트카라 부클 재킷 21세기대군부인 가디건 자켓"
    Strips leading '#'; deduplicates; max 120 chars.
    """
    parts: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
        t = text.strip().lstrip("#")
        if t and t not in seen:
            seen.add(t)
            parts.append(t)

    _add(celeb)
    _add(product_name)
    for kw in keywords:
        _add(kw)

    return " ".join(parts)[:120]


# ── Image downloader ──────────────────────────────────────────────────────────

def _dl(url: str) -> Optional[Image.Image]:
    try:
        warnings.filterwarnings("ignore")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            "Referer": "https://blog.naver.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=headers, verify=False)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


# ── Naver image search (Selenium) ────────────────────────────────────────────

def naver_image_search(query: str, max_results: int = 20) -> list[str]:
    """
    Search Naver images by keyword. Returns original image URLs (decoded from
    Naver proxy: search.pstatic.net/common/?src=<original>).

    We know this works: confirmed with class _fe_image_tab_content_thumbnail_image.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        return []

    encoded = quote(query)
    search_url = f"https://search.naver.com/search.naver?where=image&query={encoded}"

    opts = Options()
    opts.binary_location = "/usr/lib/chromium/chromium"
    for arg in [
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-gpu", "--window-size=1280,900",
        "--disable-blink-features=AutomationControlled",
    ]:
        opts.add_argument(arg)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None
    found: list[str] = []
    try:
        svc = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=svc, options=opts)
        driver.set_page_load_timeout(25)
        driver.get(search_url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "img._fe_image_tab_content_thumbnail_image")
                )
            )
        except Exception:
            time.sleep(3)

        imgs = driver.find_elements(
            By.CSS_SELECTOR, "img._fe_image_tab_content_thumbnail_image"
        )

        seen: set[str] = set()
        for img in imgs[: max_results * 2]:
            proxy_src = img.get_attribute("src") or ""
            if not proxy_src.startswith("http"):
                continue
            try:
                qs = parse_qs(urlparse(proxy_src).query)
                orig = qs.get("src", [None])[0]
                if orig and orig.startswith("http") and orig not in seen:
                    seen.add(orig)
                    found.append(orig)
                    if len(found) >= max_results:
                        break
            except Exception:
                continue

    except Exception as e:
        logging.warning("naver_image_search error: %s", e)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return found


# ── Similarity filtering ──────────────────────────────────────────────────────

def filter_similar(
    orig_img: Image.Image,
    candidate_urls: list[str],
    threshold: int = SIMILAR_THRESHOLD,
) -> list[tuple[int, str, Image.Image]]:
    """
    Download candidates, compute phash vs original.
    Returns [(diff, url, img), ...] sorted ascending by diff.
    """
    try:
        import imagehash
    except ImportError:
        logging.warning("imagehash not installed; similarity filter disabled")
        return []

    orig_hash = imagehash.phash(orig_img)
    results: list[tuple[int, str, Image.Image]] = []
    for url in candidate_urls:
        img = _dl(url)
        if img is None:
            continue
        try:
            diff = int(imagehash.phash(img) - orig_hash)
            if diff <= threshold:
                results.append((diff, url, img))
        except Exception:
            continue

    results.sort(key=lambda x: x[0])
    return results


# ── Clean image reconstruction ────────────────────────────────────────────────

def reconstruct_clean(
    orig_img: Image.Image,
    similar_images: list[Image.Image],
    watermark_regions: list[dict],
) -> Optional[Image.Image]:
    """
    Reconstruct a watermark-free image from multiple copies of the same photo.

    3+ copies → pixel-wise median
      Works because product/background pixels are identical across copies
      while each blog's watermark is at a unique position → minority = outlier.
    2  copies → fill watermarked region from the second copy
    1  copy   → return directly (caller decides whether diff is close enough)
    0  copies → return None
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    all_images = [orig_img] + similar_images
    n = len(all_images)
    if n == 0:
        return None

    iw, ih = orig_img.size

    arrays = [
        np.array(im.convert("RGB").resize((iw, ih), Image.LANCZOS))
        for im in all_images
    ]

    if n >= 3:
        # pixel-wise median — removes any per-copy overlay (watermarks)
        stack = np.stack(arrays, axis=0)
        median = np.median(stack, axis=0).astype(np.uint8)
        return Image.fromarray(median)

    elif n == 2:
        if not watermark_regions:
            return similar_images[0]   # no region info → use alternative directly
        result = arrays[0].copy()
        for r in watermark_regions:
            x1 = max(0, int(r.get("x", 0) * iw))
            y1 = max(0, int(r.get("y", 0) * ih))
            x2 = min(iw, int((r.get("x", 0) + r.get("w", 0)) * iw))
            y2 = min(ih, int((r.get("y", 0) + r.get("h", 0)) * ih))
            if x2 > x1 and y2 > y1:
                result[y1:y2, x1:x2] = arrays[1][y1:y2, x1:x2]
        return Image.fromarray(result)

    else:
        # Only 1 copy (same as the original) — nothing to combine
        return None


# ── Naver Blog Search API ─────────────────────────────────────────────────────

def naver_blog_search(
    query: str,
    client_id: str,
    client_secret: str,
    max_results: int = 20,
) -> list[dict]:
    """
    Search Naver blogs via the Open API.
    Returns list of {"url": str, "title": str, "blogname": str, "postdate": str}.
    """
    results: list[dict] = []
    display = min(max_results, 100)
    try:
        r = requests.get(
            "https://openapi.naver.com/v1/search/blog.json",
            params={"query": query, "display": display, "sort": "sim"},
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            timeout=10,
        )
        r.raise_for_status()
        for item in r.json().get("items", []):
            url = item.get("link", "")
            if url:
                results.append({
                    "url": url,
                    "title": re.sub(r"<[^>]+>", "", item.get("title", "")),
                    "blogname": item.get("bloggername", ""),
                    "postdate": item.get("postdate", ""),
                })
    except Exception as e:
        logging.warning("naver_blog_search error: %s", e)
    return results


def extract_images_from_blog_post(post_url: str) -> list[str]:
    """
    Scrape image URLs from a Naver blog post.
    Uses the mobile version (m.blog.naver.com) which renders full HTML.
    Returns CDN image URLs likely to be product photos (≥ 200px implied by URL pattern).
    """
    try:
        # Convert desktop URL to mobile
        mobile_url = re.sub(
            r"https?://blog\.naver\.com/([A-Za-z0-9_]+)/(\d+)",
            r"https://m.blog.naver.com/\1/\2",
            post_url,
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G998B) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.6099.144 Mobile Safari/537.36",
            "Referer": "https://m.blog.naver.com/",
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
        r = requests.get(mobile_url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        found: list[str] = []
        seen: set[str] = set()
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src") or ""
            if not src.startswith("http"):
                continue
            # Skip UI chrome: profile pics, icons, emoticons, buttons
            if any(x in src for x in ("blogpfthumb", "icon", "btn_", "logo", "emoticon", "sticker")):
                continue
            # Accept known Naver blog image CDNs
            if not any(x in src for x in (
                "postfiles.pstatic.net", "blogfiles.naver.net",
                "mblogthumb-phinf.pstatic.net", "cafeptthumb",
            )):
                continue
            # Strip query params to get clean URL
            clean = src.split("?")[0]
            if clean not in seen:
                seen.add(clean)
                found.append(clean)
        return found
    except Exception as e:
        logging.debug("extract_images_from_blog_post(%s): %s", post_url, e)
        return []


# ── Blog source discovery ─────────────────────────────────────────────────────

def discover_blog_sources(
    image_urls: list[str],
    blog_posts: list[dict] | None = None,
) -> list[str]:
    """
    Register newly discovered blog sources (inactive by default).
    - blog_posts: list of {"url", "blogname"} dicts from naver_blog_search
    - image_urls: CDN image URLs (used for non-Naver fashion domains)
    """
    import db as _db
    added: list[str] = []
    seen: set[str] = set()

    # Register Naver blogs found via blog search API
    if blog_posts:
        for post in blog_posts:
            url = post.get("url", "")
            m = re.match(r"https://blog\.naver\.com/([A-Za-z0-9_]+)", url)
            if not m:
                continue
            blog_id = m.group(1)
            base_url = f"https://blog.naver.com/{blog_id}"
            if base_url in seen:
                continue
            seen.add(base_url)
            blogname = post.get("blogname") or blog_id
            try:
                _db.create_source(
                    name=f"[자동발견] {blogname}",
                    url=base_url,
                    image_mapping="미괄식",
                    active=False,
                    notes="블로그 검색 API로 자동 발견",
                    rss_category="",
                )
                added.append(base_url)
                logging.info("Discovered Naver blog: %s (%s)", base_url, blogname)
            except Exception as e:
                if "UNIQUE" not in str(e):
                    logging.warning("discover_blog_sources naver: %s", e)

    # Register non-Naver fashion/blog domains from image CDN URLs
    for url in image_urls:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if not domain or "naver" in domain or "daum" in domain:
                continue
            if not any(x in domain for x in ("blog", "style", "fashion", "shop", "mall")):
                continue
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            if base_url in seen:
                continue
            seen.add(base_url)
            try:
                _db.create_source(
                    name=f"[자동발견] {domain}",
                    url=base_url,
                    image_mapping="미괄식",
                    active=False,
                    notes="유사 이미지 검색으로 자동 발견",
                    rss_category="",
                )
                added.append(base_url)
                logging.info("Discovered source: %s", base_url)
            except Exception as e:
                if "UNIQUE" not in str(e):
                    logging.warning("discover_blog_sources: %s", e)
        except Exception:
            continue

    return added


# ── Top-level orchestrator ────────────────────────────────────────────────────

def search_and_reconstruct(
    celeb: str,
    product_name: str,
    keywords: list[str],
    orig_url: str,
    watermark_regions: list[dict],
    max_posts: int = 8,
    save_sources: bool = True,
) -> dict:
    """
    Full pipeline: keyword → blog search (API) + image search → similarity filter → reconstruct.

    Returns:
      {
        "clean_image":  PIL.Image | None,
        "similar_urls": [str, ...],
        "blog_urls":    [str, ...],
        "new_sources":  [str, ...],
        "method":       "median" | "fill" | "direct" | "none",
      }
    """
    from services.settings_service import load_settings
    settings = load_settings()

    query = build_search_query(celeb, product_name, keywords)
    logging.info("search_and_reconstruct query=%r", query)

    candidate_urls: list[str] = []
    blog_posts: list[dict] = []
    # Maps image_url → blog post dict (for source registration)
    url_to_blog: dict[str, dict] = {}

    # ── 1. Naver Blog Search API (preferred when keys are configured) ──────────
    client_id = settings.naver_client_id
    client_secret = settings.naver_client_secret
    if client_id and client_secret:
        blog_posts = naver_blog_search(query, client_id, client_secret, max_results=max_posts * 3)
        logging.info("Blog search returned %d posts", len(blog_posts))
        for post in blog_posts[:max_posts]:
            imgs = extract_images_from_blog_post(post["url"])
            logging.info("  %s → %d images", post["url"], len(imgs))
            for img_url in imgs:
                url_to_blog[img_url] = post
                candidate_urls.append(img_url)

    # ── 2. Naver Image Search (Selenium fallback / supplement) ────────────────
    max_img = max(20, max_posts * 3)
    img_candidates = naver_image_search(query, max_results=max_img)
    logging.info("Naver image search returned %d candidates", len(img_candidates))
    img_set = set(candidate_urls)
    for u in img_candidates:
        if u not in img_set:
            candidate_urls.append(u)
            img_set.add(u)

    logging.info("Total candidate images: %d", len(candidate_urls))

    # ── 3. Load original image ─────────────────────────────────────────────────
    orig_img: Optional[Image.Image] = None
    if orig_url.startswith("/") or orig_url.startswith("file://"):
        local_path = orig_url.replace("file://", "")
        try:
            orig_img = Image.open(local_path).convert("RGB")
        except Exception:
            orig_img = None
    else:
        orig_img = _dl(orig_url)

    if orig_img is None:
        logging.warning("search_and_reconstruct: could not load original from %s", orig_url)
        return {
            "clean_image": None, "similar_urls": [], "blog_urls": [],
            "new_sources": [], "method": "none",
        }

    # ── 4. Similarity filter ───────────────────────────────────────────────────
    all_similar = filter_similar(orig_img, candidate_urls, threshold=SIMILAR_THRESHOLD)
    similar_urls = [u for _, u, _ in all_similar]
    logging.info("%d similar images found (threshold=%d)", len(all_similar), SIMILAR_THRESHOLD)

    same_photo = [(d, u, img) for d, u, img in all_similar if d <= SAME_PHOTO_THRESHOLD]
    same_imgs  = [img for _, _, img in same_photo]

    # ── 5. Blog source discovery — only blogs that had similar images ──────────
    new_sources: list[str] = []
    if save_sources:
        # Determine which blog posts actually contributed a similar image
        similar_set = set(similar_urls)
        contributing_blogs: list[dict] = []
        seen_blog_urls: set[str] = set()
        for img_url in similar_set:
            blog = url_to_blog.get(img_url)
            if blog and blog["url"] not in seen_blog_urls:
                seen_blog_urls.add(blog["url"])
                contributing_blogs.append(blog)
        new_sources = discover_blog_sources(
            image_urls=candidate_urls,
            blog_posts=contributing_blogs if contributing_blogs else None,
        )

    # ── 6. Reconstruct ─────────────────────────────────────────────────────────
    method = "none"
    clean: Optional[Image.Image] = None

    if len(same_imgs) >= 2:
        n = len(same_imgs) + 1
        method = "median" if n >= 3 else "fill"
        clean = reconstruct_clean(orig_img, same_imgs, watermark_regions)
    elif len(same_imgs) == 1:
        diff = same_photo[0][0]
        if diff <= DIRECT_THRESHOLD:
            clean = same_imgs[0]
            method = "direct"

    blog_urls = [p["url"] for p in blog_posts]
    return {
        "clean_image":  clean,
        "similar_urls": similar_urls,
        "blog_urls":    blog_urls,
        "new_sources":  new_sources,
        "method":       method,
    }
