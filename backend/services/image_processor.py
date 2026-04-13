"""
Image post-processing: watermark removal + brand overlay.

Pipeline per image:
1. Download the "best" image URL selected by image_matcher
2. Edge-crop: strip the outermost N pixels on all 4 sides
   (most Korean blog watermarks are stamped near edges)
3. Add our brand overlay: semi-transparent label at bottom-right
4. Optionally add a thin border / background matte

Returns a local file path (saved to TEMP_DIR) or None on failure.
"""
from __future__ import annotations

import io, os, re, tempfile, warnings
from pathlib import Path
from typing import Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont

# ── Configuration ─────────────────────────────────────────────────────────────

# Where processed images are saved (temp dir, cleared on reboot)
TEMP_DIR = Path(tempfile.gettempdir()) / "cbg_images"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Edge pixels to crop on each side (removes most corner/edge watermarks)
EDGE_CROP_PX = 18

# Brand label drawn on the processed image
BRAND_TEXT = "celeb.picks"

# Label area height as a fraction of image height
LABEL_HEIGHT_RATIO = 0.045          # ~4.5 % of image height
LABEL_BG_ALPHA = 160                # 0=transparent, 255=opaque
LABEL_BG_COLOR = (20, 20, 20)       # dark charcoal
LABEL_TEXT_COLOR = (230, 230, 230)  # light grey

# Thin outer border added after cropping
BORDER_PX = 3
BORDER_COLOR = (200, 200, 200)      # light grey

DOWNLOAD_TIMEOUT = 8

# Fonts to try for the brand label (first available wins)
_FONT_CANDIDATES = [
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
    """Derive a short safe filename from a URL."""
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", url.split("/")[-1].split("?")[0])
    return name[:60] or "image"


# ── Core processing ───────────────────────────────────────────────────────────

def _edge_crop(img: Image.Image, px: int = EDGE_CROP_PX) -> Image.Image:
    """Remove `px` pixels from every edge."""
    w, h = img.size
    # Don't crop if image is too small
    if w <= px * 4 or h <= px * 4:
        return img
    return img.crop((px, px, w - px, h - px))


def _add_border(img: Image.Image, px: int = BORDER_PX,
                color: Tuple[int, int, int] = BORDER_COLOR) -> Image.Image:
    """Add a flat-colour border around the image."""
    w, h = img.size
    bordered = Image.new("RGB", (w + px * 2, h + px * 2), color)
    bordered.paste(img, (px, px))
    return bordered


def _add_brand_label(img: Image.Image) -> Image.Image:
    """Stamp a semi-transparent brand label at the bottom-right corner."""
    w, h = img.size
    label_h = max(18, int(h * LABEL_HEIGHT_RATIO))
    font_size = max(10, label_h - 6)

    font = _get_font(font_size)

    # Measure text
    draw_tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    try:
        bbox = draw_tmp.textbbox((0, 0), BRAND_TEXT, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # Pillow < 9 fallback
        text_w, text_h = draw_tmp.textsize(BRAND_TEXT, font=font)  # type: ignore[attr-defined]

    padding = 6
    box_w = text_w + padding * 2
    box_h = label_h

    # Create overlay
    overlay = Image.new("RGBA", (box_w, box_h), (*LABEL_BG_COLOR, LABEL_BG_ALPHA))
    draw = ImageDraw.Draw(overlay)
    text_x = padding
    text_y = (box_h - text_h) // 2
    draw.text((text_x, text_y), BRAND_TEXT, font=font, fill=(*LABEL_TEXT_COLOR, 255))

    # Composite onto image
    result = img.convert("RGBA")
    paste_x = w - box_w - BORDER_PX - 2
    paste_y = h - box_h - BORDER_PX - 2
    result.paste(overlay, (paste_x, paste_y), overlay)
    return result.convert("RGB")


def process_image(url: str) -> Optional[str]:
    """
    Download, crop edges, add border + brand label, save to TEMP_DIR.
    Returns local file path on success, None on failure.
    """
    img = _download(url)
    if img is None:
        return None

    img = _edge_crop(img)
    img = _add_brand_label(img)
    img = _add_border(img)

    filename = _safe_filename(url) + ".jpg"
    out_path = TEMP_DIR / filename
    try:
        img.save(str(out_path), "JPEG", quality=88, optimize=True)
        return str(out_path)
    except Exception:
        return None


def process_items_images(items) -> list:
    """
    For each CelebItem, process the first image_url and store the local
    processed path in `processed_image_path`.  The original `image_urls`
    (network URLs) are preserved unchanged.

    Items with no image_urls are left unchanged.
    Returns the updated list.
    """
    result = []
    for item in items:
        if item.image_urls and not item.processed_image_path:
            local_path = process_image(item.image_urls[0])
            if local_path:
                item = item.model_copy(update={"processed_image_path": local_path})
        result.append(item)
    return result
