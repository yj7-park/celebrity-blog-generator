import time
import random
import requests
import pandas as pd
import xmltodict
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple

# Naver bloggers who post celebrity item content
BLOGS: List[Tuple[str, str]] = [
    ("bcf5qp11", "쇼핑"),
    ("celubdigging", "파트너스활동으로 소정 수익발생"),
    ("dalcome5", "◇궁금해◇"),
    ("dehi61", "파트너스활동으로 소정 수익발생"),
    ("fashionblog-", "방송·연예·패션"),
    ("hkh443", "추천템"),
    ("hprbel1097", "방송/패션"),
    ("hsh6566", "방송아이템"),
    ("jsodnfak", "방송정보"),
    ("phd_choi93", "패션/코디 정보"),
    ("pravas", "TV 속 상품 정보"),
    ("skywhite369", "방송v패션v맛집v제품"),
    ("lzheng", "방송그제품"),
    ("unknown0998", "정보 생활"),
    ("nemo-c", "방송제품정보"),
]

BASE_URL = "https://rss.blog.naver.com/{name}.xml"

_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://blog.naver.com/",
}


def _wait() -> None:
    time.sleep(random.uniform(0.5, 1.5))


def get_rss(name: str, folder: str) -> List[Dict]:
    try:
        url = BASE_URL.format(name=name)
        response = requests.get(url, timeout=10)
        tree = xmltodict.parse(response.text)
        items = tree["rss"]["channel"].get("item", [])
        if isinstance(items, dict):
            items = [items]
        return [
            {
                "title": x["title"],
                "url": x["guid"],
                "date": x["pubDate"],
                "tag": x.get("tag") or "",
            }
            for x in items
            if x.get("category") == folder
        ]
    except Exception:
        return []


def collect_posts(days: int = 2) -> List[Dict]:
    all_posts: List[Dict] = []
    for name, folder in BLOGS:
        all_posts.extend(get_rss(name, folder))

    if not all_posts:
        return []

    df = pd.DataFrame(all_posts)
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")

    cutoff = (pd.to_datetime("now", utc=True) - pd.DateOffset(days=days)).floor("D")
    df = df[df["date"] >= cutoff].reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return df.to_dict(orient="records")


def get_html(url: str) -> str:
    try:
        response = requests.get(url, headers=_SCRAPE_HEADERS, timeout=10)
        # Naver blog redirects to frame; extract actual content URL
        rurl = "https://blog.naver.com/" + response.text.split('src="')[2].split('"\n')[0]
        response = requests.get(rurl, headers=_SCRAPE_HEADERS, timeout=10)
        return response.text
    except Exception:
        return ""


def get_content(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        paras = soup.find_all("p", {"class": "se-text-paragraph"})
        return "\n".join(p.get_text() for p in paras).replace("\u200b", "")
    except Exception:
        return ""


def _get_redirect(url: str) -> str:
    _wait()
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
        }
        r = requests.get(url, headers=headers, allow_redirects=False, timeout=10)
        return r.headers.get("location") or r.headers.get("Location") or ""
    except Exception:
        return ""


def _get_item_name(url: str) -> str:
    try:
        return urllib.parse.unquote_plus(url.split("q=")[1].split("&src=")[0])
    except Exception:
        try:
            return urllib.parse.unquote_plus(url.split("&pageKey=")[1].split("&")[0])
        except Exception:
            return ""


def get_href(html: str) -> Dict[str, str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        result: Dict[str, str] = {}
        for a in soup.find_all("a", {"class": "se-link"}):
            href = a.get("href", "")
            if not href:
                continue
            redir = _get_redirect(href)
            if "link.coupang" in redir:
                redir = _get_redirect(redir)
            name = _get_item_name(redir).replace("\xa0", " ")
            if name:
                result[a.get_text().strip()] = name
        return result
    except Exception:
        return {}


def get_items_for_celeb(
    posts: List[Dict], celeb: str, max_posts: int = 5
) -> Tuple[Dict[str, str], List[str]]:
    celeb_posts = [p for p in posts if celeb in p.get("title", "")]
    all_items: Dict[str, str] = {}
    snippets: List[str] = []

    for post in celeb_posts[:max_posts]:
        _wait()
        html = get_html(post["url"])
        if not html:
            continue
        content = get_content(html)
        if content:
            snippets.append(content[:500])
        all_items.update(get_href(html))

    return all_items, snippets
