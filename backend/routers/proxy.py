"""
Image proxy endpoint.
Fetches external images (e.g. pstatic.net) server-side and returns them
to the browser, bypassing CORS restrictions.

Usage: GET /api/proxy/image?url=https://...
       GET /api/proxy/processed/{filename}  — serves locally-processed images
"""
from __future__ import annotations
import re
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, FileResponse
import requests

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://blog.naver.com/",
}

# Only proxy images from trusted domains
_ALLOWED_DOMAINS = (
    "pstatic.net",
    "blogfiles.naver.net",
    "postfiles.pstatic.net",
    "mblogthumb-phinf.pstatic.net",
    "img1.daumcdn.net",
    "t1.daumcdn.net",
)


@router.get("/image")
async def proxy_image(url: str = Query(..., description="Image URL to proxy")):
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    if not any(allowed in domain for allowed in _ALLOWED_DOMAINS):
        raise HTTPException(status_code=403, detail=f"Domain not allowed: {domain}")

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(
            content=resp.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/processed/{filename}")
async def serve_processed_image(filename: str):
    """Serve a locally-processed image from TEMP_DIR by filename."""
    from services.image_processor import TEMP_DIR
    # Reject path traversal attempts
    if not re.match(r'^[\w\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = TEMP_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(path), media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=3600"})
