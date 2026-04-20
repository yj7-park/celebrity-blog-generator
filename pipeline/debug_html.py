"""실제 네이버 블로그 HTML 구조 디버깅 - PostView 직접 요청"""
import requests, re, sys, json
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://blog.naver.com/",
}

TEST_CASES = [
    ("hsh6566", "223908519046"),  # 윤은혜 플랫슈즈
    ("hkh443", None),             # 추천템 (RSS에서 가져올 것)
]

import xmltodict

def get_latest_post_url(blog_id, category):
    rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
    r = requests.get(rss_url, headers=HEADERS, timeout=10, verify=False)
    tree = xmltodict.parse(r.text)
    items = tree["rss"]["channel"].get("item", [])
    if isinstance(items, dict):
        items = [items]
    for item in items:
        if item.get("category") == category:
            return item.get("guid", ""), item.get("title", "")
    return "", ""

def get_postview_html(blog_id, log_no):
    """PostView URL로 직접 요청"""
    url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}&redirect=Dlog&widgetTypeCall=true&directAccess=false"
    r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
    return r.text

def extract_log_no(url):
    """URL에서 logNo 추출"""
    m = re.search(r'/(\d{10,})', url)
    return m.group(1) if m else None

def analyze_html(html, label=""):
    soup = BeautifulSoup(html, "html.parser")
    print(f"\n{'='*60}")
    print(f"분석: {label}")
    print(f"HTML 길이: {len(html)}")

    # 텍스트 선택자들 시도
    selectors = {
        "p.se-text-paragraph": soup.select("p.se-text-paragraph"),
        ".se-module-text p": soup.select(".se-module-text p"),
        "div.se-main-container p": soup.select("div.se-main-container p"),
        ".__se_component_area p": soup.select(".__se_component_area p"),
        "p[class*='se']": soup.select("p[class*='se']"),
    }
    for sel, results in selectors.items():
        if results:
            print(f"\n텍스트 선택자 [{sel}]: {len(results)}개")
            for p in results[:2]:
                t = p.get_text(strip=True).replace('\u200b','')
                if t:
                    print(f"  > {t[:80]}")

    # 이미지 선택자들
    img_selectors = {
        "img.se-image-resource": soup.select("img.se-image-resource"),
        "img[src*='postfiles.pstatic.net']": soup.select("img[src*='postfiles.pstatic.net']"),
        "img[src*='blogfiles']": soup.select("img[src*='blogfiles']"),
        ".se-module-image img": soup.select(".se-module-image img"),
        "img[data-lazy-src]": soup.select("img[data-lazy-src]"),
    }
    for sel, results in img_selectors.items():
        if results:
            print(f"\n이미지 선택자 [{sel}]: {len(results)}개")
            for img in results[:2]:
                src = img.get("src") or img.get("data-lazy-src","")
                print(f"  > {src[:100]}")

    # 링크
    links = soup.select("a[href*='coupang'], a[href*='smartstore'], a.se-link")
    if links:
        print(f"\n링크: {len(links)}개")
        for a in links[:3]:
            print(f"  > {a.get_text(strip=True)[:30]} → {a.get('href','')[:80]}")

    # 전체 class 분포 (어떤 구조인지 파악용)
    all_classes = set()
    for tag in soup.find_all(class_=True)[:200]:
        for c in tag.get("class", []):
            if "se-" in c or "post" in c.lower():
                all_classes.add(c)
    print(f"\n관련 CSS 클래스: {sorted(all_classes)[:30]}")

    # HTML 핵심 부분 저장
    return html

# ── 실행 ──────────────────────────────────────────────────────────
print("=== hsh6566 윤은혜 플랫슈즈 PostView 직접 요청 ===")
html_pv = get_postview_html("hsh6566", "223908519046")
analyze_html(html_pv, "hsh6566/223908519046 PostView")
with open("fixtures/_debug_postview.html", "w", encoding="utf-8") as f:
    f.write(html_pv)
print("\n→ fixtures/_debug_postview.html 저장됨")

print("\n=== hkh443 추천템 최신글 ===")
url, title = get_latest_post_url("hkh443", "추천템")
print(f"URL: {url}, 제목: {title}")
log_no = extract_log_no(url)
if log_no:
    html2 = get_postview_html("hkh443", log_no)
    analyze_html(html2, f"hkh443/{log_no}")
    with open("fixtures/_debug_hkh443.html", "w", encoding="utf-8") as f:
        f.write(html2)
    print("→ fixtures/_debug_hkh443.html 저장됨")
