"""RSS/iCal feeds 생성 — 변화 감지 알림 구독용.

출력:
- `landing/static/feed/movers.xml` — 전체 Movers 통합 피드
- `landing/static/feed/industry/{id}.xml` — 산업별 피드
- `landing/static/feed/calendar.ics` — Movers 이벤트 iCal

사용자가 RSS 리더 / 캘린더 앱에 URL 붙이면 주간 변화 자동 수신.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "landing" / "static" / "map"
FEED_DIR = ROOT / "landing" / "static" / "feed"
SITE_URL = "https://eddmpython.github.io/dartlab"


def _escape(s: str) -> str:
    """문자열을 XML-safe로 이스케이프한다.

    Parameters
    ----------
    s : str
        원본 문자열.

    Returns
    -------
    str
        HTML/XML 엔티티로 이스케이프된 문자열. None이면 빈 문자열.
    """
    return html.escape(str(s or ""), quote=True)


def _rssItem(entry: dict, cat_title: str, cat_key: str) -> str:
    """movers 항목 하나를 RSS <item> XML 문자열로 변환한다.

    Parameters
    ----------
    entry : dict
        movers.json의 개별 항목 (stockCode/corpName/signal 등).
    cat_title : str
        카테고리 표시명 (예: "ROE 급등").
    cat_key : str
        카테고리 키 (guid 생성용).

    Returns
    -------
    str
        RSS <item> XML 블록.
    """
    link = f"{SITE_URL}/map?focus={entry.get('stockCode', '')}"
    title = f"[{cat_title}] {entry.get('corpName', '')} ({entry.get('industryName', '')})"
    body_parts = [entry.get("signal", "")]
    if entry.get("note"):
        body_parts.append(entry["note"])
    desc = " | ".join([p for p in body_parts if p])
    guid = f"{cat_key}-{entry.get('stockCode', '')}-{entry.get('asOfYear', '')}"
    return f"""
<item>
  <title>{_escape(title)}</title>
  <link>{_escape(link)}</link>
  <guid isPermaLink="false">{_escape(guid)}</guid>
  <category>{_escape(cat_title)}</category>
  <description>{_escape(desc)}</description>
</item>"""


def buildMoversFeed():
    """movers.json에서 전체 통합 RSS + 산업별 RSS 피드를 생성한다.

    Notes
    -----
    출력 파일:
    - ``landing/static/feed/movers.xml`` — 전체 통합 (카테고리당 30건).
    - ``landing/static/feed/industry/{id}.xml`` — 산업별.
    movers.json 없으면 스킵.
    """
    moversPath = OUT_DIR / "movers.json"
    if not moversPath.exists():
        print("  ⚠ movers.json 없음 — RSS 스킵")
        return

    movers = json.loads(moversPath.read_text(encoding="utf-8"))
    asOf = movers.get("asOf", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    FEED_DIR.mkdir(parents=True, exist_ok=True)
    (FEED_DIR / "industry").mkdir(parents=True, exist_ok=True)

    # 전체 통합 피드
    items: list[str] = []
    industryBucket: dict[str, list[str]] = {}

    for cat_key, cat in (movers.get("categories") or {}).items():
        cat_title = cat.get("title", cat_key)
        for e in cat.get("entries", [])[:30]:  # 카테고리당 30
            item = _rssItem(e, cat_title, cat_key)
            items.append(item)
            ind = e.get("industry")
            if ind:
                industryBucket.setdefault(ind, []).append(item)

    full = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>dartlab 변화 감지 (전체)</title>
<link>{SITE_URL}/changes</link>
<description>한국 상장사 이번 회계연도 급변 Top — ROE/OpMargin/매출/부채 변화</description>
<language>ko-kr</language>
<lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
<pubDate>{asOf}T00:00:00Z</pubDate>{"".join(items)}
</channel>
</rss>
"""
    (FEED_DIR / "movers.xml").write_text(full, encoding="utf-8")
    print(f"  - movers.xml: {len(items)}건")

    # 산업별 피드
    for ind, arr in industryBucket.items():
        ind_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>dartlab 변화 감지 · {ind}</title>
<link>{SITE_URL}/industry/{ind}</link>
<description>{ind} 산업 이번 회계연도 급변 회사</description>
<language>ko-kr</language>
<lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>{"".join(arr)}
</channel>
</rss>
"""
        (FEED_DIR / "industry" / f"{ind}.xml").write_text(ind_xml, encoding="utf-8")
    print(f"  - industry/*.xml: {len(industryBucket)} 산업")


def buildCalendarFeed():
    """movers.json을 iCal(.ics) 이벤트로 변환하여 캘린더 앱 연동을 지원한다.

    Notes
    -----
    출력: ``landing/static/feed/calendar.ics``.
    카테고리당 20건. movers.json 없으면 스킵.
    """
    moversPath = OUT_DIR / "movers.json"
    if not moversPath.exists():
        return

    movers = json.loads(moversPath.read_text(encoding="utf-8"))
    asOf = movers.get("asOf", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    dtstart = asOf.replace("-", "")

    events: list[str] = []
    for cat_key, cat in (movers.get("categories") or {}).items():
        cat_title = cat.get("title", cat_key)
        for e in cat.get("entries", [])[:20]:
            uid = f"{cat_key}-{e.get('stockCode', '')}-{asOf}@dartlab"
            summary = f"[{cat_title}] {e.get('corpName', '')}"
            desc = (e.get("signal") or "").replace("\n", "\\n")
            link = f"{SITE_URL}/map?focus={e.get('stockCode', '')}"
            events.append(f"""
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstart}T000000Z
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:{summary}
DESCRIPTION:{desc}
URL:{link}
END:VEVENT""")

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//dartlab//movers//KO
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:dartlab 변화 감지
X-WR-CALDESC:한국 상장사 이번 회계연도 급변 회사{"".join(events)}
END:VCALENDAR
"""
    FEED_DIR.mkdir(parents=True, exist_ok=True)
    (FEED_DIR / "calendar.ics").write_text(ics, encoding="utf-8")
    print(f"  - calendar.ics: {len(events)} 이벤트")


def main():
    """RSS + iCal 피드 빌드 진입점. buildMoversFeed + buildCalendarFeed 순차 실행."""
    print("[Feeds] RSS + iCal 생성")
    buildMoversFeed()
    buildCalendarFeed()
    print(f"완료: {FEED_DIR}")


if __name__ == "__main__":
    main()
