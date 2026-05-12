"""DART 공시 viewer 페이지 파싱 — 공용 헬퍼.

dart.fss.or.kr/dsaf001/main.do 의 공시 인덱스 페이지에서 sub-doc 메타 추출 +
report/viewer.do 의 섹션 HTML 을 텍스트(테이블 마크다운 보존)로 변환한다.

API key 무관. providers/dart/openapi/collector (key 기반 bulk 수집) 와
gather/dart/viewer (key 무관 단건 fetch) 양쪽이 import 한다.

URL 베이스:
    https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<rcept_no>
    http://dart.fss.or.kr/report/viewer.do?rcpNo=&dcmNo=&eleId=&offset=&length=&dtd=
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

DART_MAIN_BASE = "https://dart.fss.or.kr/dsaf001/main.do"
DART_VIEWER_BASE = "http://dart.fss.or.kr/report/viewer.do"

# 하위 섹션 URL 파싱용 정규식 (다중 페이지)
MULTI_PAGE_RE = re.compile(
    r"\s+node[12]\['text'\][ =]+\"(.*?)\"\;"
    r"\s+node[12]\['id'\][ =]+\"(\d+)\";"
    r"\s+node[12]\['rcpNo'\][ =]+\"(\d+)\";"
    r"\s+node[12]\['dcmNo'\][ =]+\"(\d+)\";"
    r"\s+node[12]\['eleId'\][ =]+\"(\d+)\";"
    r"\s+node[12]\['offset'\][ =]+\"(\d+)\";"
    r"\s+node[12]\['length'\][ =]+\"(\d+)\";"
    r"\s+node[12]\['dtd'\][ =]+\"(.*?)\";"
    r"\s+node[12]\['tocNo'\][ =]+\"(\d+)\";"
)

SINGLE_PAGE_RE = re.compile(r"\t\tviewDoc\('(\d+)', '(\d+)', '(\d+)', '(\d+)', '(\d+)', '(\S+)',''\)\;")


def tableToMarkdown(table) -> str:
    """HTML 테이블 → 마크다운 테이블.

    Args:
        table: 인자.

    Raises:
        없음.

    Example:
        >>> tableToMarkdown(...)

    Returns:
        <TODO: return desc> (str)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - bs4
    """
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells: list[str] = []
        for cell in tr.find_all(["td", "th"]):
            colspan = int(cell.get("colspan", 1))
            text = cell.get_text(strip=True)
            text = re.sub(r"\s+", " ", text)
            text = text.replace("|", "｜")
            cells.append(text)
            cells.extend("" for _ in range(colspan - 1))
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    maxCols = max(len(row) for row in rows)
    for row in rows:
        while len(row) < maxCols:
            row.append("")

    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * maxCols) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def htmlToText(html: str) -> str:
    """HTML → 텍스트 (테이블은 마크다운으로 보존).

    Args:
        html: 인자.

    Raises:
        없음.

    Example:
        >>> htmlToText(...)

    Returns:
        <TODO: return desc> (str)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - bs4
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "meta", "link", "header", "footer", "nav"]):
        tag.decompose()

    for table in soup.find_all("table"):
        md = tableToMarkdown(table)
        if md:
            table.replace_with(BeautifulSoup(f"\n\n{md}\n\n", "lxml"))
        else:
            table.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all(["p", "div", "li"]):
        p.insert_after("\n")

    text = soup.get_text()
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parseSubDocs(content: str, rcpNo: str) -> list[dict]:
    """공시 인덱스 페이지 HTML → 하위 섹션 [{title, url, order, rcept_no}].

    Parameters
    ----------
    content : str
        dart.fss.or.kr/dsaf001/main.do?rcpNo=<X> 의 응답 HTML.
    rcpNo : str
        접수번호 (14자리).

    Returns
    -------
    list[dict]
        ``title``, ``url`` (viewer.do 절대 URL), ``order``, ``rcept_no`` 키를 가진
        섹션 리스트. 빈 리스트면 sub-doc 없음 (비공개 공시 또는 잘못된 rcept_no).

    Raises:
        없음.

    Example:
        >>> parseSubDocs(...)

    Args:
        content: <TODO: param desc> (str)
        rcpNo: <TODO: param desc> (str)

    Returns:
        <TODO: return desc> (list[dict])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - bs4
    """
    matches = MULTI_PAGE_RE.findall(content)
    if matches:
        result = []
        for idx, m in enumerate(matches):
            params = f"rcpNo={m[2]}&dcmNo={m[3]}&eleId={m[4]}&offset={m[5]}&length={m[6]}&dtd={m[7]}"
            result.append(
                {
                    "title": m[0],
                    "url": f"{DART_VIEWER_BASE}?{params}",
                    "order": idx,
                    "rcept_no": rcpNo,
                }
            )
        return result

    matches = SINGLE_PAGE_RE.findall(content)
    if matches:
        titleTag = BeautifulSoup(content, "lxml").title
        docTitle = titleTag.text.strip() if titleTag else "unknown"
        m = matches[0]
        params = f"rcpNo={m[0]}&dcmNo={m[1]}&eleId={m[2]}&offset={m[3]}&length={m[4]}&dtd={m[5]}"
        return [
            {
                "title": docTitle,
                "url": f"{DART_VIEWER_BASE}?{params}",
                "order": 0,
                "rcept_no": rcpNo,
            }
        ]

    return []
