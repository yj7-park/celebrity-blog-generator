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
    """Download with requests, fallback to urllib.request for malformed headers."""
    try:
        warnings.filterwarnings("ignore")
        resp = requests.get(
            url, timeout=DOWNLOAD_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            verify=False,
        )
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception:
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as response:
                return Image.open(io.BytesIO(response.read())).convert("RGB")
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
    Perform cross-post visual matching and deduplication.
    1. Group by celeb
    2. Compute pHash for the primary image of every item
    3. Merge items that share the same photo (low pHash distance)
    4. For each resulting product, select the best image across all merged sources
    """
    if not items:
        return items

    # 1. Group items by celeb
    celeb_groups: Dict[str, List[CelebItem]] = {}
    for item in items:
        celeb_groups.setdefault(item.celeb, []).append(item)

    final_deduped: List[CelebItem] = []

    for celeb, group in celeb_groups.items():
        if len(group) < 2:
            final_deduped.extend(group)
            continue

        # 2. Compute pHashes for primary images
        item_hashes: List[Tuple[CelebItem, object]] = []
        for it in group:
            url = it.image_urls[0] if it.image_urls else None
            if url:
                img = _download(url)
                if img:
                    h = _phash(img)
                    if h:
                        item_hashes.append((it, h))
                        continue
            # If no image or hash, treat as unique for now
            item_hashes.append((it, None))

        # 3. Cluster items by image similarity (Union-Find style)
        merged_indices = set()
        clusters: List[List[CelebItem]] = []

        for i in range(len(item_hashes)):
            if i in merged_indices:
                continue
            
            current_cluster = [item_hashes[i][0]]
            merged_indices.add(i)
            h_i = item_hashes[i][1]

            if h_i is not None:
                for j in range(i + 1, len(item_hashes)):
                    if j in merged_indices:
                        continue
                    h_j = item_hashes[j][1]
                    if h_j is not None:
                        # Same photo threshold: very strict (distance <= 6)
                        if (h_i - h_j) <= 6:
                            current_cluster.append(item_hashes[j][0])
                            merged_indices.add(j)
            
            clusters.append(current_cluster)

        # 4. Merge each cluster into a single CelebItem
        for cluster in clusters:
            if len(cluster) == 1:
                final_deduped.append(cluster[0])
                continue

            # Merge items in cluster
            base = cluster[0].model_copy()
            all_candidates = set(base.candidate_image_urls or [])
            all_images = set(base.image_urls or [])
            all_keywords = set(base.keywords or [])

            for other in cluster[1:]:
                # Merge images
                for u in (other.image_urls or []):
                    if u: all_images.add(u)
                for u in (other.candidate_image_urls or []):
                    if u: all_candidates.add(u)
                # Merge keywords
                for kw in (other.keywords or []):
                    if kw: all_keywords.add(kw)
                # Keep longer product name
                if len(other.product_name) > len(base.product_name):
                    base.product_name = other.product_name
            
            # Select best image from merged candidates
            unique_candidates = sorted(list(all_candidates | all_images))
            best = _best_image_from_candidates(unique_candidates)
            
            if best:
                rest = [u for u in unique_candidates if u != best]
                base = base.model_copy(update={
                    "image_urls": [best],
                    "candidate_image_urls": rest,
                    "keywords": list(all_keywords)
                })
            
            final_deduped.append(base)

    return final_deduped
