"""
Image post-processing pipeline.

Pipeline per image:
1. Download the URL
2. Composite detection: wide images (aspect > 1.6) with a clear vertical seam
   are split at the seam and the first half is used
3. Background trim: solid-colour borders (white / near-black) are removed
4. Edge crop: strip outermost N pixels (removes corner watermarks)
5. Add modern minimal signature bar at the bottom
6. Add thin outer border / matte
7. Save as JPEG

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

# Edge pixels to crop on each side (removes corner/edge watermarks)
EDGE_CROP_PX = 14

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


# ── Background trimming ───────────────────────────────────────────────────────

def _trim_background(img: Image.Image, threshold: int = 18) -> Image.Image:
    """
    Remove solid-colour borders/background. Only acts when corner pixels are
    near-white (>220) or near-black (<35) — avoids cropping actual content.
    """
    w, h = img.size
    corners = [
        img.getpixel((0, 0)),
        img.getpixel((w - 1, 0)),
        img.getpixel((0, h - 1)),
        img.getpixel((w - 1, h - 1)),
    ]
    avg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))

    is_white = all(v > 220 for v in avg)
    is_dark  = all(v < 35  for v in avg)
    if not (is_white or is_dark):
        return img

    bg = avg

    def _is_bg_row(y: int) -> bool:
        step = max(1, w // 25)
        return all(abs(img.getpixel((x, y))[i] - bg[i]) <= threshold
                   for x in range(0, w, step) for i in range(3))

    def _is_bg_col(x: int) -> bool:
        step = max(1, h // 25)
        return all(abs(img.getpixel((x, y))[i] - bg[i]) <= threshold
                   for y in range(0, h, step) for i in range(3))

    top    = 0
    while top    < h // 3 and _is_bg_row(top):   top    += 1
    bottom = h - 1
    while bottom > 2 * h // 3 and _is_bg_row(bottom): bottom -= 1
    left   = 0
    while left   < w // 3 and _is_bg_col(left):  left   += 1
    right  = w - 1
    while right  > 2 * w // 3 and _is_bg_col(right):  right  -= 1

    # Only apply if we found meaningful borders (≥ 5px)
    if top < 5 and bottom > h - 6 and left < 5 and right > w - 6:
        return img

    pad = 2
    return img.crop((
        max(0, left  - pad),
        max(0, top   - pad),
        min(w, right + pad + 1),
        min(h, bottom + pad + 1),
    ))


# ── Edge crop ─────────────────────────────────────────────────────────────────

def _edge_crop(img: Image.Image, px: int = EDGE_CROP_PX) -> Image.Image:
    w, h = img.size
    if w <= px * 4 or h <= px * 4:
        return img
    return img.crop((px, px, w - px, h - px))


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

def process_image(url: str) -> Optional[str]:
    """
    Full pipeline: download → split composite → trim bg → edge crop
                   → signature → border → save JPEG.

    For composite images (wide, clear seam) the first (left) half is used.
    Returns local file path on success, None on failure.
    """
    img = _download(url)
    if img is None:
        return None

    # Composite detection: use first half if split
    parts = _detect_and_split(img)
    img = parts[0]

    img = _trim_background(img)
    img = _edge_crop(img)
    img = _add_signature(img)
    img = _add_border(img)

    filename  = _safe_filename(url) + ".jpg"
    out_path  = TEMP_DIR / filename
    try:
        img.save(str(out_path), "JPEG", quality=88, optimize=True)
        return str(out_path)
    except Exception:
        return None


def process_items_images(items) -> list:
    """
    For each CelebItem without a processed_image_path, process image_urls[0].
    Checks the pipeline cancel token between items — exits early if cancelled.
    Returns the updated list (may be partial if cancelled).
    """
    from services.cancel_token import pipeline as _pipeline_cancel

    result = []
    for item in items:
        _pipeline_cancel.check()
        if item.image_urls and not item.processed_image_path:
            local_path = process_image(item.image_urls[0])
            if local_path:
                item = item.model_copy(update={"processed_image_path": local_path})
        result.append(item)
    return result
