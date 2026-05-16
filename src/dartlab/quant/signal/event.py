"""이벤트 기반 신호 — allFilings 공시 유형 분류.

학술 근거: Tetlock (2007), Boudoukh et al. (2019).
"""

from __future__ import annotations

import logging

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import loadAllfilingsForStock

log = logging.getLogger(__name__)

_EVENT_RULES = [
    ("risk", 5, ["소송", "제재", "행정처분", "과징금", "횡령", "배임", "벌금", "위반"]),
    ("mna", 5, ["합병", "인수", "분할", "영업양수", "영업양도"]),
    ("governance", 4, ["대표이사", "이사회", "임원", "사외이사", "감사위원"]),
    ("audit", 4, ["감사", "회계", "내부통제", "감사의견"]),
    ("capital", 3, ["유상증자", "전환사채", "자사주", "감자", "무상증자", "신주인수권", "교환사채"]),
    ("disclosure", 2, ["공시변경", "정정", "기재정정"]),
]


def _classify(reportName: str) -> tuple[str, int]:
    """공시 유형 분류 + 임팩트 스코어."""
    if not reportName:
        return "routine", 1
    for etype, impact, keywords in _EVENT_RULES:
        if any(kw in reportName for kw in keywords):
            return etype, impact
    return "routine", 1


def calcEventSignal(stockCode: str, *, market: str = "auto", series: bool = False, **kwargs) -> dict:
    """공시 이벤트 기반 신호 분석 — allFilings 분류 + impact 합산.

    Capabilities:
        DART/EDGAR 전체 공시 (allFilings) 를 type 별 분류 (재무/지분/M&A/소송/
        배당/매출예측 등) + impact score 합산. high-impact 이벤트 일자 추출
        후 PEAD 윈도우 (60d) Strategy DSL 입력. 단발 이벤트 vs 누적 이벤트
        분리 인식.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".
        series: True 면 ``_series`` (high_impact_dates list, pead_window int) 추가.

    Returns:
        dict:
            - ``totalEvents`` (int): 전체 공시 수.
            - ``eventTypes`` (dict[str, int]): type 별 카운트.
            - ``impactScore`` (int): impact 합산.
            - ``eventVerdict`` (str): impact 기반 종합 라벨.
            - ``events`` (list[dict]): 시간순 (최근 N 개) (date, report,
              type, impact).
            - 또는 ``error`` (str): allFilings 부재.

    Raises:
        없음 (error 키).

    Example:
        >>> r = calcEventSignal("005930")
        >>> r["eventTypes"]
        {'재무': 12, 'M&A': 1, '지분변동': 3, ...}

    Guide:
        - 단기 (30d) M&A · 대규모 지분변동 → impact 큼.
        - 분기보고서 (재무) impact 낮음 (정기). 임시·특별 보고서 impact 큼.
        - high_impact_dates 를 OHLCV 와 매핑하면 event-study CAR 산출 가능
          (calcCAR).

    SeeAlso:
        - ``calcEarnings``: SUE/PEAD (실적 한정)
        - ``calcCAR``: event-study cumulative abnormal return
        - ``calcMomentum``: 가격 모멘텀 (이벤트 후 drift)

    Requires:
        allFilings parquet (KR/US).

    AIContext:
        eventTypes 카운트 단독 인용 금지 — 최근 N 개 events 리스트 + impact
        합산 함께. 시즌성 (분기말 보고 폭증) 고려 필요.

    LLM Specifications:
        AntiPatterns:
            - totalEvents 절대값 인용 — 회사 규모/시장에 따라 정규화 필요.
            - impactScore 동일 임계로 KR/US 직접 비교 — 시장 별 분포 다름.
        OutputSchema:
            ``{totalEvents: int, eventTypes: dict, impactScore: int,
              eventVerdict: str, events: list[dict]}``.
        Prerequisites:
            allFilings parquet (KR DART, US EDGAR 8-K/10-K).
        Freshness:
            일별 (공시 발표 직후).
        Dataflow:
            allFilings → report_nm classify → type + impact → 합산 →
            verdict 라벨 + high-impact dates.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    market = resolveMarket(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    filings = loadAllfilingsForStock(stockCode)
    if isEmptyDf(filings):
        return {**result, "error": "allFilings 데이터 없음"}

    report_col = next((c for c in ["report_nm", "report_name", "title"] if c in filings.columns), None)
    date_col = next((c for c in ["rcept_dt", "date", "filing_date"] if c in filings.columns), None)

    if report_col is None:
        return {**result, "error": "공시명 컬럼 없음", "columns": filings.columns}

    events = []
    type_counts: dict[str, int] = {}
    impact_sum = 0

    for row in filings.iter_rows(named=True):
        rname = str(row.get(report_col, ""))
        rdate = str(row.get(date_col, ""))[:10] if date_col else None
        etype, impact = _classify(rname)
        events.append({"date": rdate, "report": rname[:60], "type": etype, "impact": impact})
        type_counts[etype] = type_counts.get(etype, 0) + 1
        impact_sum += impact

    n = len(events)
    result["totalEvents"] = n
    result["eventTypes"] = type_counts
    result["impactScore"] = round(impact_sum / max(n, 1), 2)
    result["events"] = events[-20:]
    result["recentHighImpact"] = [e for e in events[-20:] if e["impact"] >= 4]

    # 종합
    high_impact = sum(1 for e in events if e["impact"] >= 4)
    result["highImpactCount"] = high_impact
    result["eventVerdict"] = "high_activity" if high_impact >= 3 else "moderate" if high_impact >= 1 else "quiet"

    if series:
        # Strategy DSL 입력: high-impact 일자만 전달, OHLCV date 매칭은 호출자가
        result["_series"] = {
            "high_impact_dates": [e["date"] for e in events if e.get("impact", 0) >= 4 and e.get("date")],
            "pead_window": 20,
        }
    return result
