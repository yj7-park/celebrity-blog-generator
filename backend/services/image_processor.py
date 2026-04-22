"""
Image post-processing pipeline.

Pipeline per image:
1. Download the URL
2. Composite detection: wide images (aspect > 1.6) with a clear vertical seam
   are split at the seam and the first half is used
3. Watermark removal — cascade:
     a. Google/Naver reverse image search → find clean original
     b. OpenCV TELEA inpainting (fast, free, works for most text/logo WMs)
     c. DALL-E 2 inpainting (best quality, requires API key)
4. Add modern minimal signature bar at the bottom
5. Save as JPEG

Returns a local file path (saved to TEMP_DIR) or None on failure.
"""
from __future__ import annotations

import io, os, re, tempfile, time, warnings
from pathlib import Path
from typing import Optional, Tuple, List
from urllib.parse import quote, unquote

import requests
from PIL import Image, ImageDraw, ImageFont

# ── Configuration ─────────────────────────────────────────────────────────────

TEMP_DIR = Path(tempfile.gettempdir()) / "cbg_images"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Signature design ──────────────────────────────────────────────────────────
SIGNATURE_TEXT       = "Extreme.T"
SIGNATURE_BAR_H      = 26
SIGNATURE_BG_COLOR   = (10, 10, 10)
SIGNATURE_BG_ALPHA   = 195
SIGNATURE_LINE_COLOR = (160, 135, 95)
SIGNATURE_TEXT_COLOR = (195, 170, 130)

BORDER_PX    = 3
BORDER_COLOR = (220, 215, 210)

DOWNLOAD_TIMEOUT = 8

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "arial.ttf",
    "Arial.ttf",
    "DejaVuSans.ttf",
    "FreeSans.ttf",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def _download(url: str) -> Optional[Image.Image]:
    try:
        warnings.filterwarnings("ignore")
        resp = requests.get(
            url, timeout=DOWNLOAD_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
            verify=False,
        )
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception:
        return None


def _safe_filename(url: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", url.split("/")[-1].split("?")[0])
    return name[:60] or "image"


# ── Composite detection & splitting ──────────────────────────────────────────

def _find_seam_column(img: Image.Image) -> Optional[int]:
    w, h = img.size
    gray = img.convert("L")
    best_col = None
    best_var = float("inf")
    c1, c2 = w // 4, 3 * w // 4
    sample_step = max(1, h // 40)
    for x in range(c1, c2):
        vals = [gray.getpixel((x, y)) for y in range(0, h, sample_step)]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        if var < best_var:
            best_var = var
            best_col = x
    return best_col if best_var < 250 else None


def _detect_and_split(img: Image.Image) -> List[Image.Image]:
    w, h = img.size
    if w / h < 1.6:
        return [img]
    seam = _find_seam_column(img)
    if seam is None:
        return [img]
    left  = img.crop((0, 0, seam, h))
    right = img.crop((seam, 0, w, h))
    min_half_w = max(150, int(w * 0.30))
    if left.width < min_half_w or right.width < min_half_w:
        return [img]
    return [left, right]


# ── Step 1: Reverse image search (Google) ─────────────────────────────────────

def _find_original_via_reverse_search(url: str) -> Optional[Image.Image]:
    """
    Use Selenium + Chromium to do a Google reverse image search.
    Returns a visually-similar image (hash diff ≤ 12) if found, else None.
    """
    import logging
    try:
        import imagehash
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        return None

    orig = _download(url)
    if not orig:
        return None

    opts = Options()
    opts.binary_location = "/usr/lib/chromium/chromium"
    for arg in [
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-gpu", "--window-size=1280,800",
        "--disable-blink-features=AutomationControlled",
    ]:
        opts.add_argument(arg)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(20)

        encoded = quote(url, safe="")
        driver.get(f"https://www.google.com/searchbyimage?image_url={encoded}&safe=off")
        time.sleep(3)

        # Collect candidate image URLs from result page links
        candidate_urls: list[str] = []
        for el in driver.find_elements(By.CSS_SELECTOR, "a"):
            href = el.get_attribute("href") or ""
            if "imgurl=" in href:
                try:
                    img_url = unquote(href.split("imgurl=")[1].split("&")[0])
                    if img_url.startswith("http") and img_url != url:
                        candidate_urls.append(img_url)
                except Exception:
                    pass

        # Also try Naver Smart Lens
        if len(candidate_urls) < 3:
            try:
                driver.get(f"https://search.naver.com/search.naver?where=image&sm=tab_jum&query={encoded}")
                time.sleep(2)
                for el in driver.find_elements(By.CSS_SELECTOR, "a.thumb img"):
                    src = el.get_attribute("src") or ""
                    if src.startswith("http"):
                        candidate_urls.append(src)
            except Exception:
                pass

        driver.quit()
        driver = None

        # Deduplicate
        seen: set[str] = set()
        unique: list[str] = []
        for u in candidate_urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)

        if not unique:
            return None

        orig_hash = imagehash.phash(orig)
        for cand_url in unique[:10]:
            cand = _download(cand_url)
            if cand is None:
                continue
            try:
                diff = imagehash.phash(cand) - orig_hash
                if diff <= 12:
                    logging.info("Reverse search: found clean original (hash diff=%d) at %s", diff, cand_url)
                    return cand
            except Exception:
                continue

    except Exception:
        import traceback
        logging.warning("Reverse image search failed: %s", traceback.format_exc())
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return None


# ── Step 2: OpenCV TELEA inpainting ──────────────────────────────────────────

def _color_watermark_mask(img_np, region: dict, bg_mask) -> "Optional[np.ndarray]":
    """
    Build a pixel-precise mask targeting the watermark within the bounding region.

    Detects teal/cyan colored text (most Korean shopping mall watermarks use this color).
    Falls back to a tight bounding-box mask if no specific color is found.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    iw = img_np.shape[1]
    ih = img_np.shape[0]
    pad = 4  # small pad — reduces boundary artifacts
    x1 = max(0,  int(region["x"] * iw) - pad)
    y1 = max(0,  int(region["y"] * ih) - pad)
    x2 = min(iw, int((region["x"] + region["w"]) * iw) + pad)
    y2 = min(ih, int((region["y"] + region["h"]) * ih) + pad)
    if x2 <= x1 or y2 <= y1:
        return None

    bbox_mask = np.zeros((ih, iw), dtype=np.uint8)
    bbox_mask[y1:y2, x1:x2] = 255
    bbox_mask[bg_mask] = 0

    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

    # Teal / cyan: OpenCV H 78-108 (= real 156-216°), moderate-high S and V
    teal = cv2.inRange(hsv, (78, 60, 100), (108, 255, 240))

    # Keep only within the bounding box
    precise = cv2.bitwise_and(teal, bbox_mask)

    if cv2.countNonZero(precise) > 30:
        # Dilate to cover the full text stroke width
        kernel = np.ones((7, 7), np.uint8)
        precise = cv2.dilate(precise, kernel, iterations=2)
        precise = cv2.bitwise_and(precise, bbox_mask)  # stay within bbox
        precise[bg_mask] = 0
        return precise

    # Fallback: bare bounding box (no extra dilation to minimise artifact spread)
    return bbox_mask


def _remove_watermark_opencv(img: Image.Image, region: dict) -> Optional[Image.Image]:
    """
    OpenCV inpainting with color-aware mask:
    1. Build pixel-precise mask via HSV color detection within the region.
    2. TELEA inpainting with larger radius.
    3. Restore original background pixels to prevent gray smudging.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    img_np = np.array(img.convert("RGB"))
    ih, iw = img_np.shape[:2]

    # Background: near-black pixels (transparent areas converted to black JPEG)
    bg = np.all(img_np <= 20, axis=2)

    mask = _color_watermark_mask(img_np, region, bg)
    if mask is None or mask.sum() == 0:
        return None

    result = cv2.inpaint(img_np, mask, inpaintRadius=12, flags=cv2.INPAINT_TELEA)

    # Restore original background to prevent boundary smudging
    result[bg] = img_np[bg]

    return Image.fromarray(result)


# ── Step 3: DALL-E 2 inpainting ──────────────────────────────────────────────

def _remove_watermark_dalle(img: Image.Image, region: dict, api_key: str) -> Optional[Image.Image]:
    """DALL-E 2 inpainting. Fallback when OpenCV result is insufficient."""
    if not api_key:
        return None

    import base64
    from openai import OpenAI

    iw, ih = img.size
    pad = 6
    x1 = max(0,  int(region["x"] * iw) - pad)
    y1 = max(0,  int(region["y"] * ih) - pad)
    x2 = min(iw, int((region["x"] + region["w"]) * iw) + pad)
    y2 = min(ih, int((region["y"] + region["h"]) * ih) + pad)

    if x2 <= x1 or y2 <= y1:
        return None

    side = max(iw, ih)
    target = 256 if side <= 256 else (512 if side <= 512 else 1024)
    scale_x, scale_y = target / iw, target / ih

    img_sq = img.convert("RGBA").resize((target, target), Image.LANCZOS)
    mask = Image.new("RGBA", (target, target), (0, 0, 0, 255))
    mx1, my1 = int(x1 * scale_x), int(y1 * scale_y)
    mx2 = min(target, int(x2 * scale_x))
    my2 = min(target, int(y2 * scale_y))
    mask.paste(Image.new("RGBA", (mx2 - mx1, my2 - my1), (0, 0, 0, 0)), (mx1, my1))

    img_buf = io.BytesIO()
    img_sq.save(img_buf, format="PNG")
    img_buf.seek(0)
    mask_buf = io.BytesIO()
    mask.save(mask_buf, format="PNG")
    mask_buf.seek(0)

    try:
        client = OpenAI(api_key=api_key)
        response = client.images.edit(
            model="dall-e-2",
            image=("image.png", img_buf, "image/png"),
            mask=("mask.png", mask_buf, "image/png"),
            prompt="seamless background, no watermark, no text overlay, natural texture",
            n=1,
            size=f"{target}x{target}",
            response_format="b64_json",
        )
        result_sq = Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json))).convert("RGB")
        result_full = result_sq.resize((iw, ih), Image.LANCZOS)
        out = img.copy()
        patch = result_full.crop((x1, y1, x2, y2))
        out.paste(patch, (x1, y1))
        return out
    except Exception:
        import logging, traceback
        logging.warning("DALL-E inpainting failed: %s", traceback.format_exc())
        return None


# ── Watermark removal orchestrator ────────────────────────────────────────────

def _remove_watermark(
    img: Image.Image,
    region: dict,
    api_key: str = "",
    source_url: str = "",
) -> Image.Image:
    """
    Cascade:
      1. Google reverse image search → clean original
      2. OpenCV TELEA inpainting (fast, free)
      3. DALL-E 2 inpainting (best quality, needs key)
    """
    import logging

    # 1. Reverse image search
    if source_url:
        clean = _find_original_via_reverse_search(source_url)
        if clean is not None:
            logging.info("Watermark removed via reverse image search")
            return clean

    # 2. OpenCV
    result = _remove_watermark_opencv(img, region)
    if result is not None:
        logging.info("Watermark removed via OpenCV TELEA inpainting")
        return result

    # 3. DALL-E
    if api_key:
        result = _remove_watermark_dalle(img, region, api_key)
        if result is not None:
            logging.info("Watermark removed via DALL-E 2 inpainting")
            return result

    logging.warning("All watermark removal methods failed; returning original")
    return img


# ── Signature bar ─────────────────────────────────────────────────────────────

def _add_signature(img: Image.Image) -> Image.Image:
    w, h = img.size
    bar_h   = SIGNATURE_BAR_H
    font_sz = 11
    font         = _get_font(font_sz)
    display_text = f"◆  {SIGNATURE_TEXT}  ◆"
    bar  = Image.new("RGBA", (w, bar_h), (*SIGNATURE_BG_COLOR, SIGNATURE_BG_ALPHA))
    draw = ImageDraw.Draw(bar)
    draw.line([(0, 0), (w, 0)], fill=(*SIGNATURE_LINE_COLOR, 220), width=1)
    try:
        bbox   = draw.textbbox((0, 0), display_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(display_text, font=font)  # type: ignore
    tx = (w - text_w) // 2
    ty = (bar_h - text_h) // 2 + 1
    draw.text((tx, ty), display_text, font=font, fill=(*SIGNATURE_TEXT_COLOR, 255))
    result = img.convert("RGBA")
    result.paste(bar, (0, h - bar_h), bar)
    return result.convert("RGB")


# ── Border ────────────────────────────────────────────────────────────────────

def _add_border(img: Image.Image, px: int = BORDER_PX,
                color: Tuple[int, int, int] = BORDER_COLOR) -> Image.Image:
    w, h = img.size
    bordered = Image.new("RGB", (w + px * 2, h + px * 2), color)
    bordered.paste(img, (px, px))
    return bordered


# ── Public API ────────────────────────────────────────────────────────────────

def process_image(
    url: str,
    watermark_regions: Optional[list[dict]] = None,
    openai_api_key: str = "",
    # legacy single-region compat
    watermark_region: Optional[dict] = None,
) -> Optional[str]:
    """
    Full pipeline: download → split composite → watermark removal → signature → save JPEG.
    watermark_regions: list of {x, y, w, h} as 0-1 fractions (all watermarks).
    """
    try:
        img = _download(url)
        if img is None:
            return None

        parts = _detect_and_split(img)
        img = parts[0]

        # Normalise to list
        regions: list[dict] = []
        if watermark_regions:
            regions = [r for r in watermark_regions if r.get("w", 0) > 0]
        elif watermark_region and watermark_region.get("w", 0) > 0:
            regions = [watermark_region]

        if regions:
            # Try reverse search once for the whole image
            clean = _find_original_via_reverse_search(url)
            if clean is not None:
                import logging
                logging.info("Watermark removed via reverse image search")
                img = clean
            else:
                # Apply inpainting for each detected watermark region
                for region in regions:
                    result_cv = _remove_watermark_opencv(img, region)
                    if result_cv is not None:
                        img = result_cv
                    elif api_key := openai_api_key:
                        result_dalle = _remove_watermark_dalle(img, region, api_key)
                        if result_dalle is not None:
                            img = result_dalle

        img = _add_signature(img)

        filename = _safe_filename(url) + ".jpg"
        out_path = TEMP_DIR / filename
        img.save(str(out_path), "JPEG", quality=88, optimize=True)
        return str(out_path)
    except Exception:
        import logging, traceback
        logging.warning("process_image failed for %s: %s", url, traceback.format_exc())
        return None


def _naver_image_search(keywords: list[str], max_results: int = 12) -> list[str]:
    """
    Naver keyword-based image search via Selenium.
    Naver image search thumbnails proxy original URLs via search.pstatic.net;
    we decode those to get the actual source image URLs.
    """
    import logging
    from urllib.parse import urlparse, parse_qs
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        return []

    query = " ".join(k for k in keywords if k)[:80]
    if not query:
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
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(25)
        driver.get(search_url)

        # Wait for Naver thumbnail images to appear
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
            if not proxy_src or not proxy_src.startswith("http"):
                continue
            # Naver proxy: https://search.pstatic.net/common/?src=<original>&type=...
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
        logging.warning("Naver image search failed: %s", e)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return found


def _google_reverse_search(url: str, max_results: int = 12) -> list[str]:
    """Google reverse image search. Usually blocked by bot detection."""
    import logging
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        return []

    opts = Options()
    opts.binary_location = "/usr/lib/chromium/chromium"
    for arg in [
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-gpu", "--window-size=1280,800",
        "--disable-blink-features=AutomationControlled",
    ]:
        opts.add_argument(arg)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None
    found: list[str] = []
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(20)

        encoded = quote(url, safe="")
        driver.get(f"https://www.google.com/searchbyimage?image_url={encoded}&safe=off")
        time.sleep(3)

        seen: set[str] = set([url])
        for el in driver.find_elements(By.CSS_SELECTOR, "a"):
            href = el.get_attribute("href") or ""
            if "imgurl=" in href:
                try:
                    img_url = unquote(href.split("imgurl=")[1].split("&")[0])
                    if img_url.startswith("http") and img_url not in seen:
                        seen.add(img_url)
                        found.append(img_url)
                        if len(found) >= max_results:
                            break
                except Exception:
                    pass
    except Exception as e:
        logging.warning("Google reverse search failed: %s", e)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return found


def reverse_search_candidates(
    url: str,
    max_results: int = 12,
    keywords: list[str] | None = None,
) -> list[str]:
    """
    Search for similar product images.
    - keywords provided → Naver keyword image search (works reliably)
    - keywords absent   → Google reverse image search (usually blocked)
    """
    if keywords:
        return _naver_image_search(keywords, max_results)
    return _google_reverse_search(url, max_results)


def process_items_images(items, openai_api_key: str = "") -> list:
    """
    For each CelebItem without a processed_image_path, process image_urls[0].
    Checks the pipeline cancel token between items.
    """
    from services.cancel_token import pipeline as _pipeline_cancel

    result = []
    for item in items:
        _pipeline_cancel.check()
        if item.image_urls and not item.processed_image_path:
            local_path = process_image(item.image_urls[0], openai_api_key=openai_api_key)
            if local_path:
                item = item.model_copy(update={"processed_image_path": local_path})
        result.append(item)
    return result
