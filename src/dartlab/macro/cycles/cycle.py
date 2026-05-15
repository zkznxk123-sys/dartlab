"""매크로 사이클 분석 — 4국면 판별 + 전환 시퀀스."""

from __future__ import annotations

from dartlab.macro.cycles.macroCycle import classifyCycle, detectTransitionSequence
from dartlab.macro.seriesFetch import (
    applyOverrides,
    collectTimeseries,
    fetchChangePct,
    fetchLatest,
    fetchYoy,
    getGather,
    recentTimeseries,
)


def _fetchIndicators(market: str, asOf: str | None = None) -> dict[str, float | None]:
    """gather에서 사이클 판별에 필요한 지표 수집.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일 (``"2024-06-30"``). ``None`` 이면 최신.

    Returns
    -------
    dict[str, float]
        None 값은 제거된 채 반환. 가능한 키:

        - hy_spread : float — HY 스프레드 (bp)
        - hy_spread_3m_change : float — HY 스프레드 3개월 변화율 (%)
        - term_spread : float — 10Y-2Y 금리차 (%p)
        - vix : float — VIX 지수 (pt)
        - gold_yoy : float — 금 가격 전년비 변화율 (%)
        - bei_10y : float — 10년 BEI 기대인플레 (%)
        - cpi_yoy : float — CPI 전년비 (%)
        - cli_mom : float — OECD CLI 전월차 (pt, KR 전용)
    """
    g = getGather(asOf)
    indicators: dict[str, float | None] = {}

    if market.upper() == "US":
        hy = fetchLatest(g, "BAMLH0A0HYM2")
        if hy is not None:
            indicators["hy_spread"] = hy * 100
        hy_chg = fetchChangePct(g, "BAMLH0A0HYM2", 63)
        if hy_chg is not None:
            indicators["hy_spread_3m_change"] = hy_chg

        indicators["term_spread"] = fetchLatest(g, "T10Y2Y")
        indicators["vix"] = fetchLatest(g, "VIXCLS")
        indicators["gold_yoy"] = fetchYoy(g, "IR14270")
        indicators["bei_10y"] = fetchLatest(g, "T10YIE")
        indicators["cpi_yoy"] = fetchYoy(g, "CPIAUCSL")

    elif market.upper() == "KR":
        from dartlab.macro.seriesFetch import fetchLatestWithPrev

        cli, cli_prev = fetchLatestWithPrev(g, "CLI")
        if cli is not None and cli_prev is not None:
            indicators["cli_mom"] = cli - cli_prev

    # None 값 제거 (classifyCycle은 키 존재 여부로 판단)
    return {k: v for k, v in indicators.items() if v is not None}


def _buildSignalHistory(market: str, asOf: str | None = None) -> dict[str, list[tuple[str, float]]] | None:
    """전환 시퀀스 순서 검증을 위한 시계열 이력 구축.

    최근 12개월 데이터를 ``[(날짜, 값)]`` 형태로 반환.

    Parameters
    ----------
    market : str
        ``"US"`` 만 지원. 그 외 시장은 ``None`` 반환.
    as_of : str | None
        기준일. ``None`` 이면 최신.

    Returns
    -------
    dict[str, list[tuple[str, float]]] | None
        신호별 최근 12개월 시계열. ``None`` = US 외 시장이거나 데이터 부재. 키:

        - hy_spread_3m_change — HY 스프레드 3개월 변화
        - gold_yoy — 금 전년비
        - long_rate_change — 10Y 국채금리 변화
        - vix — VIX 지수
        - term_spread — 10Y-2Y 금리차
        - bei_10y — 10년 BEI
    """
    if market.upper() != "US":
        return None
    g = getGather(asOf)
    history: dict[str, list[tuple[str, float]]] = {}

    # 신호 → FRED 시리즈 매핑
    seriesMap = {
        "hy_spread_3m_change": "BAMLH0A0HYM2",
        "gold_yoy": "IR14270",
        "long_rate_change": "DGS10",
        "vix": "VIXCLS",
        "term_spread": "T10Y2Y",
        "bei_10y": "T10YIE",
    }
    for key, sid in seriesMap.items():
        ts = recentTimeseries(g.macro(sid), months=12)
        if ts:
            history[key] = [(entry["date"], entry["value"]) for entry in ts if entry["value"] is not None]

    return history if history else None


def analyzeCycle(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """경제 사이클 4국면 판별 + 전환 시퀀스 감지.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.
    overrides : dict | None
        지표 강제 치환 (예: ``{"vix": 35}``).

    Returns
    -------
    dict
        - market : str — 시장 코드
        - phase : str — 국면 (``"expansion"``/``"slowdown"``/``"contraction"``/``"recovery"``)
        - phaseLabel : str — 국면 한글명 (``"확장"``/``"둔화"``/``"수축"``/``"회복"``)
        - confidence : str — 판별 신뢰도 (``"high"``/``"medium"``/``"low"``)
        - signals : list[str] — 판별에 사용된 신호 목록
        - sectorStrategy : str — 국면별 섹터 전략 가이드
        - transition : dict | None — 전환 시퀀스 (from, to, progress(%), triggered, pending, sequenceOrder, orderValid)
        - timeseries : dict — hy_spread / vix / term_spread 시계열
        - quadrant : dict | None — Bridgewater 4분면 (성장×인플레)
    """
    indicators = _fetchIndicators(market, asOf=asOf)
    if overrides:
        indicators = applyOverrides(indicators, overrides)

    cycle = classifyCycle(indicators)

    # 시계열 이력 구축 — 전환 시퀀스 순서 검증용
    history = _buildSignalHistory(market, asOf)
    transition = detectTransitionSequence(cycle.phase, indicators, history=history)

    result: dict = {
        "market": market.upper(),
        "phase": cycle.phase,
        "phaseLabel": cycle.label,
        "confidence": cycle.confidence,
        "signals": list(cycle.signals),
        "sectorStrategy": cycle.sectorStrategy,
        "transition": None,
    }

    if transition is not None:
        t_dict: dict = {
            "from": transition.fromPhase,
            "to": transition.toPhase,
            "progress": transition.progress,
            "triggered": list(transition.triggered),
            "pending": list(transition.pending),
        }
        if transition.sequenceOrder:
            t_dict["sequenceOrder"] = [{"signal": sig, "firstTriggered": dt} for sig, dt in transition.sequenceOrder]
        if transition.orderValid is not None:
            t_dict["orderValid"] = transition.orderValid
        result["transition"] = t_dict

    g = getGather(asOf)
    result["timeseries"] = collectTimeseries(
        g,
        {
            "hy_spread": "BAMLH0A0HYM2",
            "vix": "VIXCLS",
            "term_spread": "T10Y2Y",
        },
    )

    # ── Bridgewater 4 Quadrant (Growth × Inflation) ──
    try:
        from dartlab.synth.quadrant import classifyQuadrant

        if market.upper() == "US":
            # ISM PMI - 50 (성장 신호)
            ism = fetchLatest(g, "AMTMNO")
            # CPI YoY 3개월 모멘텀 (인플레 신호)
            cpiYoy = indicators.get("cpi_yoy")
            cpi_yoy_prev = fetchChangePct(g, "CPIAUCSL", 63)  # 3M ago
            if ism is not None and cpiYoy is not None:
                growthSignal = ism - 50.0
                # 인플레 모멘텀: 현재 CPI YoY 방향 (양수=상승 추세)
                inflationSignal = cpi_yoy_prev if cpi_yoy_prev is not None else 0.0
                result["quadrant"] = classifyQuadrant(growthSignal, inflationSignal)
        elif market.upper() == "KR":
            # BSI 제조업 (성장 대용치)
            bsi = fetchLatest(g, "BSI")
            cpi_yoy_kr = fetchYoy(g, "CPI")
            cpi_change = fetchChangePct(g, "CPI", 3)
            if bsi is not None and cpi_yoy_kr is not None:
                growthSignal = bsi - 100.0  # BSI 100 기준
                inflationSignal = cpi_change if cpi_change is not None else 0.0
                result["quadrant"] = classifyQuadrant(growthSignal, inflationSignal)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    return result
