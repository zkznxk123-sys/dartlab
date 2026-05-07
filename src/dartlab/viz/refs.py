"""ChartSpec evidence ref helper — drill-back 회로 식별자 + 외부 deep-link.

evidence 회로의 진입점은 두 단계다:

- **차트 단위** (``evidenceBinding``): 차트 전체가 어떤 표/계정/기간 범위에서
  파생되었는지. drawer 가 처음 열릴 때 진입점으로 쓴다.
- **데이터포인트 단위** (``series[].pointRefs``): series.data[i] 와 1:1 대응.
  차트 안 한 점을 클릭했을 때 그 점이 어떤 period 의 어떤 보고서에서 왔는지.

식별자는 모두 문자열 stable key 다. landing 측 EvidencePanel 이 같은 키를
들고 있는 row 와 join 한다.

DART 정기보고서 deep-link::

    https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<rcept_no>

페이지 anchor 는 보고서 종류에 따라 사용 가능 여부가 다르다. landing 은
``pdfPage`` 가 있으면 같은 URL 에 ``#<page>`` 를 붙인다.
"""

from __future__ import annotations

from typing import Any

# ── 식별자 빌더 ───────────────────────────────────────────────────────────


def tableRef(source: str, topic: str, periodKind: str = "") -> str:
    """차트가 파생된 표의 안정적 키.

    Examples:
        tableRef("finance", "IS", "Y") → "finance:IS:Y"
        tableRef("scan", "PEER")       → "scan:PEER"
    """
    parts = [source, topic]
    if periodKind:
        parts.append(periodKind)
    return ":".join(p for p in parts if p)


def valueRef(stockCode: str, source: str, topic: str, account: str, period: str) -> str:
    """단일 datapoint 의 안정적 키.

    Examples:
        valueRef("005930", "finance", "IS", "sales", "2024")
            → "finance:005930:IS:sales:2024"
    """
    return f"{source}:{stockCode}:{topic}:{account}:{period}"


# ── DART 외부 deep-link ───────────────────────────────────────────────────

_DART_BASE = "https://dart.fss.or.kr/dsaf001/main.do"


def filingDeepLink(rcept_no: str | None, *, page: int | None = None) -> str | None:
    """rcept_no → DART 정기보고서 원문 URL.

    rcept_no 가 비어 있으면 None.

    Examples:
        filingDeepLink("20250315000123")
            → "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250315000123"
        filingDeepLink("20250315000123", page=42)
            → "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250315000123#page=42"
    """
    if not rcept_no:
        return None
    url = f"{_DART_BASE}?rcpNo={rcept_no}"
    if page is not None:
        url = f"{url}#page={page}"
    return url


# ── ChartSpec 단위 evidence 빌더 ──────────────────────────────────────────


def chartEvidenceBinding(
    *,
    stockCode: str,
    source: str,
    topic: str,
    periodKind: str = "",
    periods: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """차트 단위 evidenceBinding dict.

    generator 가 ChartSpec dict 의 ``evidenceBinding`` 키에 그대로 넣는다.
    ``extra`` 로 source-specific 메타 (예: ``{"reportName": "사업보고서"}``)
    를 추가할 수 있다.
    """
    binding: dict[str, Any] = {
        "tableRef": tableRef(source, topic, periodKind),
        "source": source,
        "stockCode": stockCode,
        "topic": topic,
    }
    if periodKind:
        binding["periodKind"] = periodKind
    if periods:
        binding["periods"] = list(periods)
    if extra:
        binding.update(extra)
    return binding


# ── series 단위 pointRefs 빌더 ────────────────────────────────────────────


def seriesPointRefs(
    *,
    stockCode: str,
    source: str,
    topic: str,
    account: str,
    periods: list[str],
    rceptMap: dict[str, str] | None = None,
    pageMap: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """series.data[i] 와 1:1 대응하는 pointRef 리스트.

    rceptMap: ``{period: rcept_no}`` — 있으면 datapoint 별 외부 deep-link 가능.
    pageMap:  ``{period: pdf_page}`` — 정기보고서 PDF 페이지 anchor.

    rcept_no 가 없는 period 는 ``rcept_no``/``filingUrl`` 키를 생략한다.
    """
    rceptMap = rceptMap or {}
    pageMap = pageMap or {}
    refs: list[dict[str, Any]] = []
    for period in periods:
        ref: dict[str, Any] = {
            "period": period,
            "valueRef": valueRef(stockCode, source, topic, account, period),
        }
        rcept = rceptMap.get(period)
        if rcept:
            ref["rcept_no"] = rcept
            page = pageMap.get(period)
            url = filingDeepLink(rcept, page=page)
            if url:
                ref["filingUrl"] = url
                if page is not None:
                    ref["pdfPage"] = page
        refs.append(ref)
    return refs
