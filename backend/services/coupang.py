"""
Coupang Partners Affiliate API service.
Adapted from Blog-main/CoupangSearcher.py
"""
from __future__ import annotations
import hashlib, hmac, json, re, requests
from time import gmtime, strftime
from typing import List, Optional
from urllib import parse
from models.schemas import AppSettings, CoupangProduct


def _generate_hmac(method: str, path_with_query: str, access_key: str, secret_key: str) -> str:
    """Generate HMAC-SHA256 authorization header for Coupang API."""
    path, *query = path_with_query.split("?")
    datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
    message = datetime_gmt + method + path + (query[0] if query else "")
    signature = hmac.new(
        bytes(secret_key, "utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_gmt}, signature={signature}"


def search_products(keyword: str, settings: AppSettings, limit: int = 10) -> List[CoupangProduct]:
    """Search Coupang affiliate products by keyword."""
    encoded_kw = parse.quote(keyword)
    path = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={encoded_kw}&limit={limit}&imageSize=400x400"
    auth = _generate_hmac("GET", path, settings.coupang_access_key, settings.coupang_secret_key)

    try:
        resp = requests.get(
            url=f"{settings.coupang_domain}{path}",
            headers={"Authorization": auth, "Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Coupang API 오류: {e}")

    product_data = data.get("data", {}).get("productData", [])
    results: List[CoupangProduct] = []
    for p in product_data:
        price_raw = p.get("productPrice", 0)
        try:
            price_int = int(str(price_raw).replace(",", ""))
        except Exception:
            price_int = 0

        results.append(CoupangProduct(
            product_id=str(p.get("productId", "")),
            product_name=p.get("productName", ""),
            product_image=p.get("productImage", ""),
            product_url=p.get("productUrl", ""),
            product_price=price_int,
            affiliate_url=p.get("productUrl", ""),
        ))
    return results


def shorten_url(long_url: str) -> str:
    """Shorten a URL using IS.GD API."""
    if "is.gd" in long_url:
        return long_url
    try:
        resp = requests.get(
            "https://is.gd/create.php",
            params={"format": "json", "url": long_url},
            timeout=8,
        )
        data = resp.json()
        return data.get("shorturl", long_url)
    except Exception:
        return long_url


def get_affiliate_landing_url(product_url: str, settings: AppSettings) -> str:
    """Convert a regular Coupang product URL to an affiliate tracking URL."""
    encoded = parse.quote(product_url)
    path = f"/v2/providers/affiliate_open_api/apis/openapi/links/products/byUrls?urls={encoded}"
    auth = _generate_hmac("GET", path, settings.coupang_access_key, settings.coupang_secret_key)
    try:
        resp = requests.get(
            url=f"{settings.coupang_domain}{path}",
            headers={"Authorization": auth, "Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        links = data.get("data", [])
        if links:
            return links[0].get("landingUrl", product_url)
    except Exception:
        pass
    return product_url
