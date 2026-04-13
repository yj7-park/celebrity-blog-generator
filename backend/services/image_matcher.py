"""
Cross-post image matching using perceptual hashing.

Algorithm:
1. Group items by celeb + normalized product_name
2. For groups with 2+ items (same product across multiple posts),
   collect all candidate_image_urls from every post
3. Compute pHash for each candidate image
4. Find the most "central" image — lowest average hamming distance to all others
   (= the image closest to the "median" appearance, ignoring per-blog watermarks)
5. Update image_urls on all matching items with the winner

For single-post items, fall back to the LLM-selected image_urls as-is.
"""
from __future__ import annotations

import io, re, warnings
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image

from models.schemas import CelebItem

# Lazy-import imagehash — gracefully degrade if not installed
try:
    import imagehash as _imagehash
    _HAVE_IMAGEHASH = True
except ImportError:
    _HAVE_IMAGEHASH = False

# pHash distance threshold: images with distance ≤ this are "the same photo"
SIMILAR_THRESHOLD = 12
CANDIDATE_LIMIT = 12   # max candidates per group to keep download time bounded
DOWNLOAD_TIMEOUT = 6


# ── helpers ───────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """Lowercase + remove non-alphanumeric for product-name grouping."""
    return re.sub(r"[^a-z0-9가-힣]", "", name.lower())


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


def _phash(img: Image.Image):
    """Return perceptual hash or None."""
    if not _HAVE_IMAGEHASH:
        return None
    try:
        return _imagehash.phash(img)
    except Exception:
        return None


# ── core matching ─────────────────────────────────────────────────────────────

def _best_image_from_candidates(candidates: List[str]) -> Optional[str]:
    """
    Given a deduplicated list of candidate URLs from multiple posts,
    return the URL of the most central image (lowest avg pHash distance).

    Falls back to first URL if imagehash is unavailable or all downloads fail.
    """
    if not candidates:
        return None
    if len(candidates) == 1 or not _HAVE_IMAGEHASH:
        return candidates[0]

    # Limit to avoid excessive downloads
    candidates = candidates[:CANDIDATE_LIMIT]

    hashed: List[Tuple[str, object]] = []
    for url in candidates:
        img = _download(url)
        if img is None:
            continue
        h = _phash(img)
        if h is not None:
            hashed.append((url, h))

    if not hashed:
        return candidates[0]
    if len(hashed) == 1:
        return hashed[0][0]

    # Find image with lowest average distance to all others
    best_url = hashed[0][0]
    min_avg = float("inf")
    for i, (url_i, h_i) in enumerate(hashed):
        others = [h_j for url_j, h_j in hashed if url_j != url_i]
        if not others:
            continue
        avg = sum(h_i - h_j for h_j in others) / len(others)
        if avg < min_avg:
            min_avg = avg
            best_url = url_i

    return best_url


def cross_match_items(items: List[CelebItem]) -> List[CelebItem]:
    """
    For each group of items sharing the same celeb + product_name,
    run cross-post image matching and update image_urls to the best image.

    Items that appear only in a single post are left unchanged.
    """
    if not items:
        return items

    # Group indices by celeb::normalized_product_name
    groups: Dict[str, List[int]] = {}
    for i, item in enumerate(items):
        key = f"{item.celeb}::{_normalize(item.product_name)}"
        groups.setdefault(key, []).append(i)

    result: List[CelebItem] = list(items)

    for key, indices in groups.items():
        if len(indices) < 2:
            continue  # single-post item — skip expensive matching

        # Collect all candidate URLs across posts (deduplicated, preserving order)
        seen: set[str] = set()
        all_candidates: List[str] = []
        for idx in indices:
            for url in (items[idx].candidate_image_urls or items[idx].image_urls):
                if url and url not in seen:
                    seen.add(url)
                    all_candidates.append(url)

        if not all_candidates:
            continue

        best = _best_image_from_candidates(all_candidates)
        if best:
            for idx in indices:
                result[idx] = result[idx].model_copy(update={"image_urls": [best]})

    return result
