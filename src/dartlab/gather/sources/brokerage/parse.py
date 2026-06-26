"""증권사별 보드 HTML → ReportMeta 파싱 어댑터 (내부).

보드 DOM 이 제각각이라(미래에셋 표·NH ul>li·유안타 표) 범용 셀렉터 하나로는 부족 —
증권사별 어댑터로 분기한다(P0 실측 결론). 본문은 받지 않고 메타만 추출.
공개 진입점은 mixins/research.py 의 brokerageReports — 본 파서들은 내부 헬퍼.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .schema import ReportMeta

_MIRAE_VIEW = "https://securities.miraeasset.com/bbs/board/message/view.do"


def _normDate(s: str) -> str:
    """'2026.06.26'·'2026/06/26' 류 날짜를 'YYYY-MM-DD' 로 정규화 (구분자 통일·앞 10자)."""
    return re.sub(r"[./]", "-", (s or "").strip())[:10]


def _parseMiraeasset(html: str, label: str, srcUrl: str) -> list[ReportMeta]:
    """미래에셋 보드 표(작성일·제목·첨부·작성자) → ReportMeta. 링크는 view() → view.do URL.

    Args:
        html: 보드 list.do 응답 HTML (cp949 디코드 후).
        label: 카테고리 라벨 = reportType.
        srcUrl: 링크 추출 실패 시 fallback URL.

    Returns:
        list[ReportMeta] — 표 행마다 1건. 표 미발견 시 빈 리스트.

    Example::

        _parseMiraeasset(html, "기업분석", url)
    """
    soup = BeautifulSoup(html, "lxml")
    table = None
    for tb in soup.find_all("table"):
        ths = [th.get_text(strip=True) for th in tb.find_all("th")]
        if "제목" in ths and "작성일" in ths:
            table = tb
            break
    if table is None:
        return []
    out: list[ReportMeta] = []
    body = table.find("tbody") or table
    for tr in body.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        link = tds[1].find("a")
        href = link.get("href", "") if link else ""
        m = re.search(r"view\('(\d+)','(\d+)'\)", href)
        url = f"{_MIRAE_VIEW}?messageId={m.group(1)}&categoryId={m.group(2)}" if m else srcUrl
        out.append(
            ReportMeta(
                broker="miraeasset",
                brokerName="미래에셋",
                title=tds[1].get_text(" ", strip=True),
                url=url,
                pubDate=_normDate(tds[0].get_text(strip=True)),
                reportType=label,
                author=tds[3].get_text(strip=True) or None,
            )
        )
    return out


def _parseNh(html: str, label: str, srcUrl: str) -> list[ReportMeta]:
    """NH 모바일 보드 ul>li>a → ReportMeta. reportType 은 행별 p.sort 우선(없으면 라벨).

    Args:
        html: boardList 응답 HTML.
        label: 카테고리 라벨 (p.sort 부재 시 fallback reportType).
        srcUrl: 링크 부재 시 fallback URL.

    Returns:
        list[ReportMeta] — p.tit 있는 항목마다 1건.

    Example::

        _parseNh(html, "기업분석", url)
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[ReportMeta] = []
    for a in soup.select("ul li a"):
        tit = a.select_one("p.tit")
        if tit is None:
            continue
        sort = a.select_one("p.sort")
        name = a.select_one("span.info_name")
        date = a.select_one("span.info_date")
        href = a.get("href", "")
        url = ("https://m.nhqv.com" + href) if href.startswith("/") else (href or srcUrl)
        out.append(
            ReportMeta(
                broker="nh",
                brokerName="NH투자",
                title=tit.get_text(" ", strip=True),
                url=url,
                pubDate=_normDate(date.get_text(strip=True) if date else ""),
                reportType=(sort.get_text(strip=True) if sort else None) or label,
                author=name.get_text(strip=True) if name else None,
            )
        )
    return out


def _parseYuanta(html: str, label: str, srcUrl: str) -> list[ReportMeta]:
    """유안타 rs_list 표(날짜·제목·파일·-·저자·조회수) → ReportMeta. 링크 href=# → srcUrl.

    Args:
        html: rs_list.cmd 응답 HTML.
        label: 카테고리 라벨 = reportType.
        srcUrl: 링크 href=# 라 카테고리 URL 을 그대로 사용.

    Returns:
        list[ReportMeta] — td 5개 이상 행마다 1건.

    Example::

        _parseYuanta(html, "투자전략", url)
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[ReportMeta] = []
    body = soup.find("tbody") or soup
    for tr in body.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        author = tds[4].get_text(" ", strip=True).replace("관심 애널리스트", "").strip()
        out.append(
            ReportMeta(
                broker="yuanta",
                brokerName="유안타",
                title=tds[1].get_text(" ", strip=True),
                url=srcUrl,
                pubDate=_normDate(tds[0].get_text(strip=True)),
                reportType=label,
                author=author or None,
            )
        )
    return out


PARSERS = {
    "miraeasset": _parseMiraeasset,
    "nh": _parseNh,
    "yuanta": _parseYuanta,
}
