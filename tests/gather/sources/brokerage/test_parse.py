"""brokerage.parse 단위 테스트 — 증권사별 파서 어댑터 (픽스처, 네트워크 0)."""

from __future__ import annotations

import pytest

from dartlab.gather.sources.brokerage.parse import (
    _normDate,
    _parseBookook,
    _parseHanyang,
    _parseMiraeasset,
    _parseNh,
)

pytestmark = pytest.mark.unit

_MIRAE_HTML = """
<table><thead><tr><th>작성일</th><th>제목</th><th>첨부</th><th>작성자</th></tr></thead>
<tbody>
<tr><td>2026-06-25</td>
    <td><a href="javascript:view('111','1800')">삼성전자 (005930/매수) 좋다</a></td>
    <td></td><td>홍길동</td></tr>
</tbody></table>
"""

_NH_HTML = """
<ul><li><a href="/research/authCheck?type=view&rshPprNo=123">
<p class="sort">기업</p><p class="tit">[한세실업] 과도한 우려</p>
<p class="info"><span class="info_name">정지윤</span><span class="info_date">2026.06.26</span></p>
</a></li></ul>
"""

_HANYANG_HTML = """
<table><tbody>
<tr><td>2052</td>
    <td><a href="/board/researchAnalyzeCompany/detail/2087;jsessionid=ABC?pageIndex=1">[06/25] 리브스메드(491000) : 바이오 약세장 추천종목</a>
        <a href="https://www.hygood.co.kr/download?atchFileId=FILE_001">첨부</a></td>
    <td>2026.06.25</td><td></td><td>304</td></tr>
</tbody></table>
"""

# 부국: 기업분석(6셀: 번호·날짜·제목·-·저자·조회수) + 시황(5셀: 저자 없음·끝=조회수) 실제 양식.
_BOOKOOK_HTML = """
<table><tbody>
<tr><td>2399</td><td>2026/06/22</td>
    <td><a href="javascript:void(0);" onclick="viewDetailContent('2512')">에스바이오메딕스(304360) - Not Rated</a></td>
    <td></td><td>유대웅</td><td>79</td></tr>
<tr><td>3430</td><td>2026/06/26</td>
    <td><a href="javascript:__fileDownload('1','6328','x.pdf','re02','2026/06')">아침종합자료(06/26/금)</a></td>
    <td></td><td>10</td></tr>
</tbody></table>
"""


def test_norm_date() -> None:
    assert _normDate("2026.06.26") == "2026-06-26"
    assert _normDate("2026/06/26") == "2026-06-26"
    assert _normDate("") == ""


def test_parse_miraeasset() -> None:
    rows = _parseMiraeasset(_MIRAE_HTML, "기업분석", "https://fallback")
    assert len(rows) == 1
    r = rows[0]
    assert r.broker == "miraeasset"
    assert r.pubDate == "2026-06-25"
    assert r.reportType == "기업분석"
    assert r.author == "홍길동"
    assert "messageId=111" in r.url and "categoryId=1800" in r.url


def test_parse_miraeasset_no_table() -> None:
    assert _parseMiraeasset("<html><body>없음</body></html>", "기업분석", "u") == []


def test_parse_nh() -> None:
    rows = _parseNh(_NH_HTML, "기업분석", "https://fallback")
    assert len(rows) == 1
    r = rows[0]
    assert r.broker == "nh"
    assert r.title == "[한세실업] 과도한 우려"
    assert r.reportType == "기업"  # 행별 p.sort 우선
    assert r.author == "정지윤"
    assert r.pubDate == "2026-06-26"
    assert r.url.startswith("https://m.nhqv.com/research/authCheck")


def test_parse_hanyang() -> None:
    rows = _parseHanyang(_HANYANG_HTML, "기업분석", "https://fallback")
    assert len(rows) == 1
    r = rows[0]
    assert r.broker == "hanyang"
    assert r.reportType == "기업분석"
    assert r.pubDate == "2026-06-25"
    assert "리브스메드(491000)" in r.title
    # detail 링크 = 한양 자기 서버, jsessionid 꼬리 제거
    assert r.url == "https://www.hygood.co.kr/board/researchAnalyzeCompany/detail/2087"


def test_parse_hanyang_no_detail() -> None:
    assert _parseHanyang("<table><tbody><tr><td>없음</td></tr></tbody></table>", "기업분석", "u") == []


def test_parse_bookook() -> None:
    rows = _parseBookook(_BOOKOOK_HTML, "기업분석", "https://www.bookook.co.kr/research/research_5")
    assert len(rows) == 2
    r0 = rows[0]
    assert r0.broker == "bookook"
    assert r0.pubDate == "2026-06-22"
    assert "에스바이오메딕스(304360)" in r0.title
    assert r0.author == "유대웅"
    assert r0.url == "https://www.bookook.co.kr/research/research_5"  # per-report URL 부재 → 보드 URL
    # 시황 행: 마지막 셀이 조회수(숫자) → author None
    assert rows[1].author is None
    assert "아침종합자료" in rows[1].title


def test_parse_bookook_no_date() -> None:
    assert _parseBookook("<table><tbody><tr><td>헤더</td><td>제목</td></tr></tbody></table>", "기업분석", "u") == []
