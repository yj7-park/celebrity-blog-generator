"""
Naver blog RSS collection and HTML scraping.
Supports ordered_blocks (text + image interleaved) for LLM extraction.
"""
from __future__ import annotations
import re, time
from typing import Callable, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from models.schemas import OrderedBlock, PostItem, ScrapedPostData

# ── Blog list (blogId, categoryFolder) ───────────────────────────────────────
BLOGS: List[Tuple[str, str]] = [
    ("hsh6566",     "쇼핑"),
    ("hkh443",      "코스트코"),
    ("hprbel1097",  "방송아이템"),
    ("jsodnfak",    "먹거리"),
    ("fashionblog", "파트너스활동으로 소정 수익발생"),
    ("bcf5qp11",    "쇼핑"),
    ("celubdigging", "파트너스활동으로 소정 수익발생"),
    ("dalcome5",    "◇궁금해◇"),
    ("greenp77",    "쇼핑"),
    ("jiyeon_style","패션"),
    ("beauty_daily","뷰티"),
    ("kdrama_item", "방송아이템"),
    ("celeb_pick",  "셀럽픽"),
    ("stylenote_kr","스타일"),
    ("kfashion_lab","패션"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}


# ── RSS collection ────────────────────────────────────────────────────────────

def _get_rss(name: str, folder: str) -> List[PostItem]:
    try:
        import xmltodict
        resp = requests.get(
            f"https://rss.blog.naver.com/{name}.xml",
            headers=HEADERS, timeout=8, verify=False,
        )
        resp.raise_for_status()
        doc = xmltodict.parse(resp.text)
        items = doc.get("rss", {}).get("channel", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        result: List[PostItem] = []
        for it in items:
            cats = it.get("category", "")
            if isinstance(cats, list):
                cats = " ".join(cats)
            if folder.lower() not in str(cats).lower():
                continue
            guid = it.get("guid", "")
            url = (guid.get("#text", "") if isinstance(guid, dict) else guid) or ""
            result.append(PostItem(
                title=str(it.get("title", "")),
                url=str(url),
                date=str(it.get("pubDate", "")),
                tag=str(it.get("category", "")),
            ))
        return result
    except Exception:
        return []


def collect_posts(
    days: int = 2,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> List[PostItem]:
    import urllib3
    urllib3.disable_warnings()
    cutoff = time.time() - days * 86400
    all_posts: List[PostItem] = []
    total = len(BLOGS)

    for i, (name, folder) in enumerate(BLOGS):
        posts = _get_rss(name, folder)
        all_posts.extend(posts)
        if on_progress:
            on_progress(i + 1, total)

    valid: List[PostItem] = []
    for p in all_posts:
        try:
            from email.utils import parsedate_to_datetime
            t = parsedate_to_datetime(p.date).timestamp()
            if t >= cutoff:
                valid.append(p)
        except Exception:
            pass
    valid.sort(key=lambda p: p.date, reverse=True)
    return valid


# ── HTML scraping ─────────────────────────────────────────────────────────────

def _parse_naver_url(url: str) -> Optional[Tuple[str, str]]:
    m = re.search(r'blog\.naver\.com/([^/?#]+)/(\d+)', url)
    if not m:
        m = re.search(r'blogId=([^&]+).*logNo=(\d+)', url)
    return (m.group(1), m.group(2)) if m else None


def _build_postview_url(blog_id: str, log_no: str) -> str:
    return (
        f"https://blog.naver.com/PostView.naver"
        f"?blogId={blog_id}&logNo={log_no}"
        f"&redirect=Dlog&widgetTypeCall=true&directAccess=false"
    )


def _fetch_html(url: str, timeout: int = 12) -> str:
    import urllib3
    urllib3.disable_warnings()
    resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
    resp.raise_for_status()
    return resp.text


def _parse_naver_html(html: str, title: str, post_url: str) -> ScrapedPostData:
    soup = BeautifulSoup(html, "lxml")

    # Images
    image_urls: List[str] = []
    seen_imgs: set[str] = set()
    for img in soup.select("img.se-image-resource, img[src*='postfiles.pstatic.net']"):
        src = img.get("src") or img.get("data-lazy-src") or ""
        if src and "pstatic.net" in src:
            src = re.sub(r'\?type=\w+', '?type=w966', src)
            if src not in seen_imgs:
                seen_imgs.add(src)
                image_urls.append(src)

    # Paragraphs
    paragraphs: List[str] = []
    for p in soup.select("p.se-text-paragraph"):
        t = (p.get_text() or "").replace("\u200b", "").replace("\xa0", " ").strip()
        if t:
            paragraphs.append(t)

    # Ordered blocks
    ordered_blocks: List[OrderedBlock] = []
    container = soup.select_one("div.se-main-container, div.__se_component_area")
    if container:
        def walk(node):
            cls = node.get("class") or []
            if node.name == "p" and "se-text-paragraph" in cls:
                t = (node.get_text() or "").replace("\u200b", "").replace("\xa0", " ").strip()
                if t:
                    ordered_blocks.append(OrderedBlock(type="text", content=t))
            elif node.name == "img" and (
                "se-image-resource" in cls
                or "postfiles.pstatic.net" in (node.get("src") or "")
            ):
                src = node.get("src") or node.get("data-lazy-src") or ""
                if src and "pstatic.net" in src:
                    src = re.sub(r'\?type=\w+', '?type=w966', src)
                    ordered_blocks.append(OrderedBlock(type="image", url=src))
            else:
                for child in node.children:
                    if hasattr(child, "name") and child.name:
                        walk(child)

        for child in container.children:
            if hasattr(child, "name") and child.name:
                walk(child)

    # Links — include all known short-URL domains + coupang / smartstore
    _LINK_KEYWORDS = (
        "coupang", "smartstore", "naver.me",
        "vvd.bz", "han.gl", "me2.do", "url.kr",
        "bit.ly", "t.co", "tinyurl.com", "ow.ly", "goo.gl",
        "smarturl.it", "rebrand.ly", "buff.ly", "cutt.ly",
        "vo.la", "c11.kr", "mrk.kr", "lrl.kr", "glink.page",
        "coupa.ng", "link.coupang.com",
    )
    _selector = ", ".join(
        f"a[href*='{kw}']" for kw in _LINK_KEYWORDS
    ) + ", a.se-link"
    links: List[dict] = []
    seen_hrefs: set[str] = set()
    for a in soup.select(_selector):
        href = a.get("href") or ""
        text = (a.get_text() or "").strip()
        if href.startswith("http") and href not in seen_hrefs:
            seen_hrefs.add(href)
            links.append({"text": text, "href": href})

    return ScrapedPostData(
        ordered_blocks=ordered_blocks,
        image_urls=image_urls,
        paragraphs=paragraphs,
        links=links,
        post_url=post_url,
        title=title,
    )


def scrape_post(post: PostItem) -> Optional[ScrapedPostData]:
    try:
        parsed = _parse_naver_url(post.url)
        if not parsed:
            return None
        pv_url = _build_postview_url(*parsed)
        html = _fetch_html(pv_url)
        data = _parse_naver_html(html, post.title, post.url)
        return data if (data.paragraphs or data.image_urls) else None
    except Exception:
        return None


def scrape_multiple_posts(
    posts: List[PostItem],
    max_posts: int = 10,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> List[ScrapedPostData]:
    targets = posts[:max_posts]
    results: List[ScrapedPostData] = []
    for i, post in enumerate(targets):
        data = scrape_post(post)
        if data:
            results.append(data)
        if on_progress:
            on_progress(i + 1, len(targets))
    return results
