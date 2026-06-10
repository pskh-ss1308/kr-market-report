"""뉴스 RSS 수집 — 한국/미국 경제·증시 헤드라인.

각 기사에 출처(매체명)와 원문 링크를 보존한다(출처 명확성 요구사항).
RSS 주소는 변경될 수 있으므로 피드별 실패는 건너뛴다.
"""
from __future__ import annotations
import time
import feedparser


def _publisher(parsed, entry) -> str:
    feed_title = getattr(parsed.feed, "title", "") if parsed else ""
    return getattr(entry, "source", {}).get("title", feed_title) or feed_title or "RSS"


def _fetch_feed(url: str, limit: int) -> list[dict]:
    items: list[dict] = []
    try:
        parsed = feedparser.parse(url)
        pub = getattr(parsed.feed, "title", "") or url
        for e in parsed.entries[:limit]:
            ts = None
            if getattr(e, "published_parsed", None):
                ts = time.strftime("%Y-%m-%d %H:%M", e.published_parsed)
            items.append({
                "title": (getattr(e, "title", "") or "").strip(),
                "link": getattr(e, "link", ""),
                "publisher": pub,
                "published": ts,
            })
    except Exception as ex:  # noqa: BLE001
        print(f"[collect_news] 피드 실패 {url}: {ex}")
    return items


def collect_news(rss_kr: list[str], rss_us: list[str], limit: int = 6) -> dict:
    kr, us = [], []
    for u in rss_kr:
        kr.extend(_fetch_feed(u, limit))
    for u in rss_us:
        us.extend(_fetch_feed(u, limit))

    # 제목 기준 중복 제거
    def _dedupe(lst):
        seen, out = set(), []
        for it in lst:
            key = it["title"].lower()
            if key and key not in seen:
                seen.add(key)
                out.append(it)
        return out

    return {"kr": _dedupe(kr), "us": _dedupe(us)}


if __name__ == "__main__":
    import json
    from config import NEWS_RSS_KR, NEWS_RSS_US
    print(json.dumps(collect_news(NEWS_RSS_KR, NEWS_RSS_US), ensure_ascii=False, indent=2))
