"""DART 공시 viewer 페이지 파싱 — 공용 헬퍼.

dart.fss.or.kr/dsaf001/main.do 의 공시 인덱스 페이지에서 sub-doc 메타 추출 +
report/viewer.do 의 섹션 HTML 을 텍스트(테이블 마크다운 보존)로 변환한다.

API key 무관. providers/dart/openapi/collector (key 기반 bulk 수집) 와
gather/dart/viewer (key 무관 단건 fetch) 양쪽이 import 한다. L0 core 격상으로
gather→providers cross 를 해소한다.

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
    """BeautifulSoup ``<table>`` element → markdown table 문자열.

    Capabilities:
        - HTML 표 (``<tr>`` + ``<td>``/``<th>``) 를 GitHub-flavored markdown table 로 변환.
        - colspan 자동 확장 (1 cell → 빈 cell 추가).
        - cell 안 pipe (``|``) 를 fullwidth (``｜``) 로 escape — markdown 구문 충돌 회피.
        - 첫 row 는 헤더, 두 번째 row 는 separator (``---``) 자동 삽입.

    Args:
        table: BeautifulSoup ``Tag`` 객체 (``<table>`` element). ``find_all('tr')`` 호출
            가능해야.

    Returns:
        str — markdown table. 빈 table 이면 ``""``.

    Example:
        >>> from bs4 import BeautifulSoup
        >>> html = "<table><tr><th>항목</th><th>값</th></tr><tr><td>매출</td><td>100</td></tr></table>"
        >>> table = BeautifulSoup(html, "lxml").find("table")
        >>> print(tableToMarkdown(table))
        | 항목 | 값 |
        | --- | --- |
        | 매출 | 100 |

    Guide:
        - "공시 HTML 표 → markdown" → ``tableToMarkdown(soup.find("table"))``.
        - sections 빌더가 본문 표를 markdown 으로 저장할 때 호출.
        - 표 안 pipe 문자가 있어도 ``｜`` 로 자동 escape — caller 후처리 불필요.

    SeeAlso:
        - ``htmlToText`` — 본 함수를 내부 사용하는 텍스트 변환.
        - ``parseSubDocs`` — DART viewer page 의 sub-doc 메타 추출.
        - ``horizontalizeTableBlock`` — markdown table 후처리 (sections 정규화).

    Requires:
        - beautifulsoup4 (``bs4.Tag.find_all``) — caller 가 BS4 객체 전달.
        - re — pipe escape + whitespace 정규화.

    AIContext:
        ``Company.panel("BS")`` 의 본문 표 → markdown evidence 변환 시 background.
        caller 는 빈 string 반환 시 "표 부재" 메시지 준비.

    LLM Specifications:
        AntiPatterns:
            - ``table`` 이 string 또는 None → ``find_all`` AttributeError 가능.
              caller 가 BS4 Tag 검증 필수.
            - colspan="0" 또는 음수 → int 변환 OSError 가능 (현재 미가드).
        OutputSchema:
            - str — markdown table (헤더 + separator + 데이터 rows).
            - 빈 table → ``""``.
        Prerequisites:
            - beautifulsoup4 + lxml 또는 html.parser.
        Freshness:
            - pure function (BS4 객체만 의존).
        Dataflow:
            - DART viewer HTML → BeautifulSoup parse → 본 함수 → sections content cell.
        TargetMarkets:
            - 일반 — HTML table 표준 형식이면 KR/US/JP 모두 변환 가능.

    Raises:
        없음.
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
    """HTML → 텍스트 (테이블은 markdown 으로 보존).

    Capabilities:
        - HTML 본문에서 ``<script>``/``<style>``/``<meta>``/``<header>``/``<footer>``/
          ``<nav>`` 같은 chrome 요소 제거.
        - ``<table>`` 은 ``tableToMarkdown`` 으로 변환해 markdown 으로 inline 유지 — 표
          데이터 보존.
        - ``<br>`` → ``\\n``, ``<p>``/``<div>``/``<li>`` 끝에 ``\\n`` 삽입해 가독성.
        - 연속 빈 줄 (3 개+) → 2 개로 축약.

    Args:
        html: 원본 HTML 문자열 (DART viewer 응답 또는 임의 HTML).

    Returns:
        str — 표는 markdown table, 본문은 plain text. 양 끝 whitespace strip.

    Example:
        >>> htmlToText("<p>안녕</p><p>세상</p>")
        '안녕\\n세상'
        >>> htmlToText("<table><tr><td>a</td><td>b</td></tr></table>")  # doctest: +ELLIPSIS
        '...| a | b |...'

    Guide:
        - "공시 viewer HTML 텍스트 추출" → ``htmlToText(resp.text)``.
        - 표가 있는 본문 → markdown 보존, AI evidence 로 인용 시 그대로 사용 가능.
        - script/style 자동 제거 — sanitization 추가 불필요.

    SeeAlso:
        - ``tableToMarkdown`` — 표 변환 (본 함수 내부 호출).
        - ``parseSubDocs`` — sub-doc 메타 추출 (별도 단계).
        - ``dartlab.providers.dart.openapi`` — viewer.do HTTP 호출자.

    Requires:
        - beautifulsoup4 + lxml — HTML 파싱.
        - re — 연속 빈 줄 축약.

    AIContext:
        DART viewer 응답 본문 → evidence text 변환 시 표준 entry point. caller 는
        evidence 인용 시 ``[EXTERNAL CONTENT START — untrusted ...]`` 마커로 wrap 의무
        (``runtime.workbenchEvidenceFlow``).

    LLM Specifications:
        AntiPatterns:
            - 매우 큰 HTML (>1MB) 입력 → lxml 메모리 부하 가능. caller 가 chunk 분할 권장.
            - sanitization 의도 없이 호출 → script/style 제거는 부산물, 본 목적 아님.
            - HTML 이 BeautifulSoup 파싱 실패 (binary 등) → lxml 이 silent 빈 결과.
        OutputSchema:
            - str — markdown + plain text 혼합.
            - 빈 입력 → ``""`` (strip 후).
        Prerequisites:
            - lxml C-extension 설치 (uv 가 표준 install).
        Freshness:
            - pure function — 외부 의존 0.
        Dataflow:
            - DART viewer.do HTTP 응답 → 본 함수 → docs builder.
        TargetMarkets:
            - KR (DART), US (EDGAR 10-K filing HTML — 동일 패턴), JP (EDINET).

    Raises:
        없음.
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
    """공시 인덱스 페이지 HTML → 하위 섹션 메타 list.

    Capabilities:
        - DART viewer index page (``dsaf001/main.do?rcpNo=<X>``) 응답 HTML 에서
          JS 변수 ``node1``/``node2`` 또는 inline ``viewDoc('...')`` 호출 정규식 매칭 →
          sub-doc 메타 추출.
        - multi-page (목차 형식) 와 single-page (단일 본문) 양쪽 패턴 자동 분기.
        - viewer.do 절대 URL 빌드 (``rcptNo``/``dcmNo``/``eleId``/``offset``/``length``/
          ``dtd`` query) — caller 가 그대로 GET 요청 가능.

    Args:
        content: viewer index page 응답 HTML 문자열. UTF-8 또는 EUC-KR 디코딩 후.
        rcpNo: 14 자리 접수번호 (DART 공시 unique ID).

    Returns:
        list[dict] — 각 sub-doc dict: ``title`` (섹션 제목) · ``url`` (viewer.do 절대 URL)
        · ``order`` (목차 순서, 0 부터) · ``rcept_no`` (인자 rcpNo 그대로). 빈 list 면
        sub-doc 부재 (비공개 공시 / 잘못된 rcpNo / index page 형식 변경).

    Example:
        >>> # 실 viewer HTML 응답 가정:
        >>> html = "node1[0] = '0'; node1[1] = '20240101000123'; "
        >>> # parseSubDocs(html, "20240101000123") → [...] 또는 빈 list
        >>> parseSubDocs("", "00000000000000")  # 빈 입력
        []

    Guide:
        - "rcept_no 로 공시 본문 sub-doc 목록" → ``parseSubDocs(html, rcpNo)``.
        - 결과 각 ``url`` 은 GET 호출 즉시 가능 — query string 완전.
        - ``title`` 은 한국어 (예 "I. 회사의 개요").

    SeeAlso:
        - ``dartlab.gather.dart.collector.DocsCollector`` — 본 함수의 caller.
        - ``htmlToText`` — sub-doc HTML 내용 추출.

    Requires:
        - re — JS 변수 + URL 패턴 정규식.
        - bs4 — single-page 분기에서 ``<title>`` 추출.

    AIContext:
        Ask Workbench 가 rcept_no 만 알고 공시 본문 인용하려 할 때 background. AI tool
        ``dart_fetch_raw`` (예정) 가 본 함수 결과 → viewer.do GET → htmlToText 파이프라인.

    LLM Specifications:
        AntiPatterns:
            - rcpNo 형식 검증 안 하고 호출 → 빈 list 반환 (오류 X). caller 가 사전
              ``re.match(r"^\\d{14}$", rcpNo)`` 검증 권장.
            - content 가 EUC-KR 인코딩 깨진 상태 → 정규식 매칭 일부 실패 가능.
            - JS 변수 패턴이 DART 페이지 개편으로 변경되면 silent 빈 list — version 가드 필요.
        OutputSchema:
            - list[dict] — 각 dict 의 4 key (title / url / order / rcept_no).
            - title: str (한국어).
            - url: str (https://dart.fss.or.kr/report/viewer.do?...).
            - order: int (0-indexed).
            - rcept_no: str (14 자리).
        Prerequisites:
            - viewer index page HTTP 응답 (인자 ``content``) 사전 fetch.
        Freshness:
            - pure function (HTML 입력만 의존).
            - DART page schema 의존 — 페이지 개편 시 패턴 재정의 필요 (1 회/년 정도).
        Dataflow:
            - DART viewer index HTTP → 본 함수 → caller 가 viewer.do 각 URL GET →
              htmlToText.
        TargetMarkets:
            - KR (DART) 전용. EDGAR/EDINET 은 별도 sub-doc 구조.

    Raises:
        없음.
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
