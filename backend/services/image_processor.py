"""
Image post-processing pipeline.

Pipeline per image:
1. Download the URL
2. Composite detection: wide images (aspect > 1.6) with a clear vertical seam
   are split at the seam and the first half is used
3. Watermark removal (optional, only when region provided)
4. Add modern minimal signature bar at the bottom
5. Save as JPEG

Returns a local file path (saved to TEMP_DIR) or None on failure.
"""
from __future__ import annotations

import io, os, re, tempfile, warnings
from pathlib import Path
from typing import Optional, Tuple, List

import requests
from PIL import Image, ImageDraw, ImageFont

# ── Configuration ─────────────────────────────────────────────────────────────

TEMP_DIR = Path(tempfile.gettempdir()) / "cbg_images"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Signature design ──────────────────────────────────────────────────────────
SIGNATURE_TEXT       = "celeb.picks"
SIGNATURE_BAR_H      = 26          # bar height in px
SIGNATURE_BG_COLOR   = (10, 10, 10)
SIGNATURE_BG_ALPHA   = 195         # 0=transparent, 255=opaque
SIGNATURE_LINE_COLOR = (160, 135, 95)   # warm gold line above bar
SIGNATURE_TEXT_COLOR = (195, 170, 130)  # warm gold-beige text

# Thin outer border
BORDER_PX    = 3
BORDER_COLOR = (220, 215, 210)     # warm light grey

DOWNLOAD_TIMEOUT = 8

# Fonts (first available wins)
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
    """
    Look for a near-uniform vertical band in the center half of a wide image.
    Returns the column index of the seam, or None if no clear seam found.
    Uses sampled rows for performance.
    """
    w, h = img.size
    gray = img.convert("L")

    best_col = None
    best_var = float("inf")

    c1, c2 = w // 4, 3 * w // 4
    sample_step = max(1, h // 40)   # ~40 sample rows per column

    for x in range(c1, c2):
        vals = [gray.getpixel((x, y)) for y in range(0, h, sample_step)]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        if var < best_var:
            best_var = var
            best_col = x

    # Threshold: only split if variance is very low (clear uniform seam)
    return best_col if best_var < 250 else None


def _detect_and_split(img: Image.Image) -> List[Image.Image]:
    """
    If the image is wide (aspect > 1.6) and has a clear vertical seam,
    split it and return [left_half, right_half].
    Otherwise return [img].

    Both halves must be at least 30 % of the original width (and at least
    150 px) — this prevents false-positive splits on blog-header images
    where a narrow sidebar column happens to have low pixel variance.
    """
    w, h = img.size
    if w / h < 1.6:
        return [img]

    seam = _find_seam_column(img)
    if seam is None:
        return [img]

    left  = img.crop((0, 0, seam, h))
    right = img.crop((seam, 0, w, h))

    # Reject if either half is too narrow relative to the original
    min_half_w = max(150, int(w * 0.30))
    if left.width < min_half_w or right.width < min_half_w:
        return [img]

    return [left, right]


# ── Watermark removal (DALL-E 2 inpainting) ─────────────────────────────────

def _remove_watermark(img: Image.Image, region: dict, api_key: str = "") -> Image.Image:
    """
    Inpaint the watermark region using OpenAI DALL-E 2 images.edit.

    Sends the full image + a mask (transparent = fill) to DALL-E 2 and pastes
    the inpainted patch back onto the original at full resolution.

    Falls back to returning the unmodified image if api_key is missing or the
    API call fails.
    """
    if not api_key:
        return img

    import base64
    from openai import OpenAI

    iw, ih = img.size

    # Pixel coords of watermark region (with small padding)
    pad = 6
    x1 = max(0,  int(region["x"] * iw) - pad)
    y1 = max(0,  int(region["y"] * ih) - pad)
    x2 = min(iw, int((region["x"] + region["w"]) * iw) + pad)
    y2 = min(ih, int((region["y"] + region["h"]) * ih) + pad)

    if x2 <= x1 or y2 <= y1:
        return img

    # DALL-E 2 requires square PNG at 256 / 512 / 1024 px
    side = max(iw, ih)
    target = 256 if side <= 256 else (512 if side <= 512 else 1024)

    scale_x, scale_y = target / iw, target / ih
    mx1 = int(x1 * scale_x)
    my1 = int(y1 * scale_y)
    mx2 = min(target, int(x2 * scale_x))
    my2 = min(target, int(y2 * scale_y))

    # Resize image to square RGBA
    img_sq = img.convert("RGBA").resize((target, target), Image.LANCZOS)

    # Mask: fully opaque everywhere except watermark region (transparent = fill)
    mask = Image.new("RGBA", (target, target), (0, 0, 0, 255))
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
            image=img_buf,
            mask=mask_buf,
            prompt="seamless background, no watermark, no text overlay, natural texture",
            n=1,
            size=f"{target}x{target}",
            response_format="b64_json",
        )
        result_sq = Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json))).convert("RGB")
    except Exception:
        import logging, traceback
        logging.warning("DALL-E watermark removal failed: %s", traceback.format_exc())
        return img

    # Paste only the inpainted region back onto the original-size image
    # (avoids degrading the rest of the image through resize round-trips)
    result_sq_full = result_sq.resize((iw, ih), Image.LANCZOS)
    out = img.copy()
    patch = result_sq_full.crop((x1, y1, x2, y2))
    out.paste(patch, (x1, y1))
    return out


# ── Signature bar (modern minimal) ───────────────────────────────────────────

def _add_signature(img: Image.Image) -> Image.Image:
    """
    Stamp a modern minimal signature bar at the bottom of the image.

    Layout (bottom N px):
      ─────────── gold line (1px) ─────────────
      ◆  celeb.picks  ◆   (centred, warm gold)
    """
    w, h = img.size
    bar_h   = SIGNATURE_BAR_H
    font_sz = 11

    font         = _get_font(font_sz)
    display_text = f"\u25C6  {SIGNATURE_TEXT}  \u25C6"   # ◆ … ◆

    # Build the bar layer
    bar  = Image.new("RGBA", (w, bar_h), (*SIGNATURE_BG_COLOR, SIGNATURE_BG_ALPHA))
    draw = ImageDraw.Draw(bar)

    # Gold top line
    draw.line([(0, 0), (w, 0)], fill=(*SIGNATURE_LINE_COLOR, 220), width=1)

    # Measure + centre text
    try:
        bbox   = draw.textbbox((0, 0), display_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(display_text, font=font)  # type: ignore

    tx = (w - text_w) // 2
    ty = (bar_h - text_h) // 2 + 1   # +1 nudge down from top line
    draw.text((tx, ty), display_text, font=font,
              fill=(*SIGNATURE_TEXT_COLOR, 255))

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
    watermark_region: Optional[dict] = None,
    openai_api_key: str = "",
) -> Optional[str]:
    """
    Full pipeline: download → split composite → watermark removal → signature → save JPEG.

    watermark_region: optional {x, y, w, h} as 0-1 fractions (from image_analyzer).
    openai_api_key: used for DALL-E 2 inpainting; skips watermark removal if empty.
    """
    try:
        img = _download(url)
        if img is None:
            return None

        parts = _detect_and_split(img)
        img = parts[0]

        if watermark_region and watermark_region.get("w", 0) > 0:
            img = _remove_watermark(img, watermark_region, openai_api_key)

        img = _add_signature(img)

        filename = _safe_filename(url) + ".jpg"
        out_path = TEMP_DIR / filename
        img.save(str(out_path), "JPEG", quality=88, optimize=True)
        return str(out_path)
    except Exception:
        import logging, traceback
        logging.warning("process_image failed for %s: %s", url, traceback.format_exc())
        return None


def process_items_images(items, openai_api_key: str = "") -> list:
    """
    For each CelebItem without a processed_image_path, process image_urls[0].
    Checks the pipeline cancel token between items — exits early if cancelled.
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
