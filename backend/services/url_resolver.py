"""
Short URL resolver.

Korean affiliate / influencer blogs use many link-shortening services.
This module follows HTTP redirects to recover the final destination URL,
then optionally rewrites it to a Coupang affiliate URL.

Known short-URL domains encountered in Korean blogs:
  vvd.bz        — Coupang viral-marketing shortener
  coupa.ng       — Coupang official short URL
  link.coupang.com — already an affiliate URL (no resolve needed)
  han.gl         — Korean URL shortener (한글닷컴)
  naver.me       — Naver short URL
  me2.do         — Korean (legacy me2day)
  url.kr         — Korean URL shortener
  bit.ly         — Bitly (global)
  t.co           — Twitter/X
  tinyurl.com    — TinyURL
  ow.ly          — Hootsuite
  is.gd          — IS.GD (we also emit these as output)
  goo.gl         — Google (deprecated but still seen)
  smarturl.it    — SmartURL
  rebrand.ly     — Rebrandly
  buff.ly        — Buffer
  cutt.ly        — Cutt.ly
"""
from __future__ import annotations
import re
import requests
from urllib.parse import urlparse

# Domains that are already final affiliate URLs — do not attempt to resolve
_ALREADY_AFFILIATE = {
    "link.coupang.com",
    "is.gd",
    "coupa.ng",
}

# Known short-URL domains — resolve these
_SHORT_URL_DOMAINS = {
    "vvd.bz",
    "han.gl",
    "naver.me",
    "me2.do",
    "url.kr",
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "ow.ly",
    "goo.gl",
    "smarturl.it",
    "rebrand.ly",
    "buff.ly",
    "cutt.ly",
    "vo.la",
    "c11.kr",
    "mrk.kr",
    "lrl.kr",
    "glink.page",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_TIMEOUT = 6  # seconds per request


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lstrip("www.")
    except Exception:
        return ""


def is_short_url(url: str) -> bool:
    """Return True if the URL looks like a known short-link service."""
    d = _domain(url)
    return d in _SHORT_URL_DOMAINS


def resolve(url: str, max_redirects: int = 10) -> str:
    """
    Follow redirects and return the final URL.
    Returns the original URL on any error.
    Falls through immediately if the URL is already a final affiliate URL.
    """
    if not url or not url.startswith("http"):
        return url

    d = _domain(url)
    if d in _ALREADY_AFFILIATE:
        return url

    # Only spend time resolving if it looks like a shortener
    if d not in _SHORT_URL_DOMAINS:
        return url

    try:
        resp = requests.head(
            url,
            headers=_HEADERS,
            allow_redirects=True,
            timeout=_TIMEOUT,
        )
        final = resp.url
        # HEAD can sometimes not follow all redirects on some servers;
        # fall back to GET if the result still looks short.
        if _domain(final) in _SHORT_URL_DOMAINS:
            resp = requests.get(
                url,
                headers=_HEADERS,
                allow_redirects=True,
                timeout=_TIMEOUT,
                stream=True,  # don't download body
            )
            final = resp.url
            resp.close()
        return final or url
    except Exception:
        return url


def resolve_links(links: list[dict]) -> list[dict]:
    """
    Resolve short URLs in a list of {'text': ..., 'href': ...} dicts.
    Returns a new list with href replaced by the resolved URL.
    """
    resolved = []
    for lk in links:
        href = lk.get("href", "")
        final = resolve(href)
        resolved.append({**lk, "href": final})
    return resolved


def extract_coupang_url(url: str) -> str:
    """
    If the resolved URL contains a coupang product URL, return it.
    Otherwise return the URL as-is.
    """
    if "coupang.com" in url or "coupa.ng" in url:
        return url
    return url
