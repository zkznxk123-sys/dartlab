"""매크로 사이클 분석 — 4국면 판별 + 전환 시퀀스."""

from __future__ import annotations

from dartlab.core.finance.macroCycle import classifyCycle, detectTransitionSequence
from dartlab.macro._helpers import (
    apply_overrides,
    collect_timeseries,
    fetch_change_pct,
    fetch_latest,
    fetch_yoy,
    get_gather,
    recent_timeseries,
)


def _fetch_indicators(market: str, as_of: str | None = None) -> dict[str, float | None]:
    """gather에서 사이클 판별에 필요한 지표 수집."""
    g = get_gather(as_of)
    indicators: dict[str, float | None] = {}

    if market.upper() == "US":
        hy = fetch_latest(g, "BAMLH0A0HYM2")
        if hy is not None:
            indicators["hy_spread"] = hy * 100
        hy_chg = fetch_change_pct(g, "BAMLH0A0HYM2", 63)
        if hy_chg is not None:
            indicators["hy_spread_3m_change"] = hy_chg

        indicators["term_spread"] = fetch_latest(g, "T10Y2Y")
        indicators["vix"] = fetch_latest(g, "VIXCLS")
        indicators["gold_yoy"] = fetch_yoy(g, "GOLDAMGBD228NLBM")
        indicators["bei_10y"] = fetch_latest(g, "T10YIE")
        indicators["cpi_yoy"] = fetch_yoy(g, "CPIAUCSL")

    elif market.upper() == "KR":
        from dartlab.macro._helpers import fetch_latest_with_prev

        cli, cli_prev = fetch_latest_with_prev(g, "CLI")
        if cli is not None and cli_prev is not None:
            indicators["cli_mom"] = cli - cli_prev

    # None 값 제거 (classifyCycle은 키 존재 여부로 판단)
    return {k: v for k, v in indicators.items() if v is not None}


def _build_signal_history(market: str, as_of: str | None = None) -> dict[str, list[tuple[str, float]]] | None:
    """전환 시퀀스 순서 검증을 위한 시계열 이력 구축.

    최근 12개월 데이터를 [(날짜, 값)] 형태로 반환.
    """
    if market.upper() != "US":
        return None
    g = get_gather(as_of)
    history: dict[str, list[tuple[str, float]]] = {}

    # 신호 → FRED 시리즈 매핑
    series_map = {
        "hy_spread_3m_change": "BAMLH0A0HYM2",
        "gold_yoy": "GOLDAMGBD228NLBM",
        "long_rate_change": "DGS10",
        "vix": "VIXCLS",
        "term_spread": "T10Y2Y",
        "bei_10y": "T10YIE",
    }
    for key, sid in series_map.items():
        ts = recent_timeseries(g.macro(sid), months=12)
        if ts:
            history[key] = [(entry["date"], entry["value"]) for entry in ts if entry["value"] is not None]

    return history if history else None


def analyze_cycle(*, market: str = "US", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """경제 사이클 분석."""
    indicators = _fetch_indicators(market, as_of=as_of)
    if overrides:
        indicators = apply_overrides(indicators, overrides)

    cycle = classifyCycle(indicators)

    # 시계열 이력 구축 — 전환 시퀀스 순서 검증용
    history = _build_signal_history(market, as_of)
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

    g = get_gather(as_of)
    result["timeseries"] = collect_timeseries(
        g,
        {
            "hy_spread": "BAMLH0A0HYM2",
            "vix": "VIXCLS",
            "term_spread": "T10Y2Y",
        },
    )

    return result
