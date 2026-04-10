"""
Phase 1: Fixture Collection (실제 HTML 구조 기반)
PostView URL로 직접 요청해서 파싱 후 fixtures/ 에 저장.
"""
import json, time, random, re, os, sys, warnings
import requests
from bs4 import BeautifulSoup
import xmltodict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding="utf-8")

BLOGS = [
    ("hkh443",    "추천템"),
    ("hsh6566",   "방송아이템"),
    ("fashionblog-", "방송·연예·패션"),
    ("celubdigging", "파트너스활동으로 소정 수익발생"),
    ("hprbel1097", "방송/패션"),
]

BASE_RSS = "https://rss.blog.naver.com/{name}.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://blog.naver.com/",
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
os.makedirs(OUT_DIR, exist_ok=True)

def wait(lo=0.8, hi=1.8):
    time.sleep(random.uniform(lo, hi))


# ── RSS 수집 ──────────────────────────────────────────────────────
def get_rss(name, folder, max_items=3):
    url = BASE_RSS.format(name=name)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        tree = xmltodict.parse(r.text)
        items = tree["rss"]["channel"].get("item", [])
        if isinstance(items, dict):
            items = [items]
        filtered = [x for x in items if x.get("category") == folder]
        return filtered[:max_items]
    except Exception as e:
        print(f"  RSS 실패 {name}: {e}")
        return []


# ── PostView URL로 직접 HTML 수집 ─────────────────────────────────
def extract_log_no(url):
    m = re.search(r'/(\d{10,})', url)
    if m:
        return m.group(1)
    m = re.search(r'logNo=(\d+)', url)
    return m.group(1) if m else None

def get_postview_html(blog_id, log_no):
    url = (
        f"https://blog.naver.com/PostView.naver"
        f"?blogId={blog_id}&logNo={log_no}"
        f"&redirect=Dlog&widgetTypeCall=true&directAccess=false"
    )
    wait()
    r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
    return r.text


# ── HTML 파싱 ─────────────────────────────────────────────────────
def resolve_short_url(url, timeout=5):
    """단축 URL(vvd.bz 등) → 최종 URL 추적"""
    try:
        r = requests.head(url, headers=HEADERS, allow_redirects=True,
                          timeout=timeout, verify=False)
        return r.url
    except Exception:
        try:
            r = requests.get(url, headers=HEADERS, allow_redirects=True,
                             timeout=timeout, verify=False)
            return r.url
        except Exception:
            return url

def parse_item_name(url):
    """쿠팡/스마트스토어 URL에서 상품명 추출"""
    try:
        from urllib.parse import urlparse, parse_qs, unquote_plus
        u = urlparse(url)
        qs = parse_qs(u.query)
        for key in ['q', 'pageKey', 'keyword']:
            if key in qs:
                return unquote_plus(qs[key][0])
        # 스마트스토어: /products/{id} 형태
        if 'smartstore' in url:
            parts = u.path.strip('/').split('/')
            if len(parts) >= 2:
                return unquote_plus(parts[-1]).replace('-', ' ')
    except Exception:
        pass
    return ""

def parse_blog_html(html, blog_id):
    soup = BeautifulSoup(html, "html.parser")

    # ── 텍스트 단락 (순서 보존) ──
    paragraphs = []
    for p in soup.select("p.se-text-paragraph"):
        t = p.get_text(strip=True).replace("\u200b", "").replace("\xa0", " ")
        if t:
            paragraphs.append(t)

    # ── 이미지 (순서 보존, 원본 해상도) ──
    image_urls = []
    for img in soup.select("img.se-image-resource, img[src*='postfiles.pstatic.net']"):
        src = img.get("src") or img.get("data-lazy-src") or ""
        if src and "pstatic.net" in src:
            src = re.sub(r'\?type=\w+', '?type=w966', src)
            if src not in image_urls:
                image_urls.append(src)

    # ── 텍스트+이미지 순서 보존 블록 (LLM 매칭용) ──
    ordered_blocks = []
    container = soup.select_one("div.se-main-container, div.__se_component_area")
    if container:
        for tag in container.descendants:
            if getattr(tag, 'name', None) == 'p' and 'se-text-paragraph' in (tag.get('class') or []):
                t = tag.get_text(strip=True).replace("\u200b", "").replace("\xa0", " ")
                if t:
                    ordered_blocks.append({"type": "text", "content": t})
            elif getattr(tag, 'name', None) == 'img':
                src = tag.get("src") or tag.get("data-lazy-src") or ""
                if src and "pstatic.net" in src:
                    src = re.sub(r'\?type=\w+', '?type=w966', src)
                    ordered_blocks.append({"type": "image", "url": src})

    # ── 링크 (단축 URL 포함) ──
    raw_links = []
    for a in soup.select("a.se-link, a[href*='coupang'], a[href*='smartstore'], a[href*='vvd.bz'], a[href*='link.naver']"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and href.startswith("http"):
            raw_links.append({"text": text, "href": href})

    # 단축 URL 해제
    resolved_links = []
    for link in raw_links:
        href = link["href"]
        if any(x in href for x in ["vvd.bz", "bit.ly", "goo.gl", "tinyurl"]):
            resolved = resolve_short_url(href)
            wait(0.3, 0.8)
        else:
            resolved = href
        item_name = parse_item_name(resolved)
        resolved_links.append({
            "text": link["text"],
            "original_url": href,
            "resolved_url": resolved,
            "item_name": item_name,
        })

    return {
        "paragraphs": paragraphs,
        "image_urls": image_urls,
        "ordered_blocks": ordered_blocks,
        "links": resolved_links,
    }


# ── 메인 ─────────────────────────────────────────────────────────
def main():
    all_fixtures = []

    for name, folder in BLOGS:
        print(f"\n[{name}] RSS 수집 중...")
        rss_items = get_rss(name, folder)
        print(f"  {len(rss_items)}개 게시글")

        for item in rss_items:
            title  = item.get("title", "")
            url    = item.get("guid", "")
            date   = item.get("pubDate", "")
            log_no = extract_log_no(url)
            if not log_no:
                print(f"  logNo 추출 실패: {url}")
                continue

            print(f"  > {title[:60]}")
            html = get_postview_html(name, log_no)
            parsed = parse_blog_html(html, name)

            print(f"    단락:{len(parsed['paragraphs'])}  이미지:{len(parsed['image_urls'])}  링크:{len(parsed['links'])}")

            fixture = {
                "blog_id":  name,
                "category": folder,
                "title":    title,
                "url":      url,
                "log_no":   log_no,
                "date":     date,
                "parsed":   parsed,
            }
            all_fixtures.append(fixture)

            safe = re.sub(r'[^\w가-힣]', '_', title)[:35]
            path = os.path.join(OUT_DIR, f"{name}_{safe}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(fixture, f, ensure_ascii=False, indent=2)

    out_path = os.path.join(OUT_DIR, "_all_fixtures.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_fixtures, f, ensure_ascii=False, indent=2)
    print(f"\n완료: {len(all_fixtures)}개 수집 → {out_path}")

if __name__ == "__main__":
    main()
