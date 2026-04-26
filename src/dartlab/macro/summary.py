"""매크로 종합 분석 — 전체 축 종합 매트릭스."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _scoreCycle(cycle: dict) -> tuple[float, list[str]]:
    phase = cycle.get("phase", "")
    label = cycle.get("phaseLabel", "")
    if phase in ("recovery", "expansion"):
        return 1.0, [f"사이클 {label} — 우호적"]
    if phase == "contraction":
        return -1.5, [f"사이클 {label} — 비우호적"]
    if phase == "slowdown":
        return -0.5, [f"사이클 {label} — 주의"]
    return 0.0, []


def _scoreRates(rates: dict) -> tuple[float, list[str]]:
    direction = rates.get("outlook", {}).get("direction", "")
    if direction == "cut":
        return 0.5, ["금리 인하 기대 — 유동성 우호적"]
    if direction == "hike":
        return -0.5, ["금리 인상 가능 — 유동성 비우호적"]
    return 0.0, []


def _scoreSentiment(sentiment: dict) -> tuple[float, list[str]]:
    fg = sentiment.get("fearGreed")
    if fg is None:
        return 0.0, []
    fg_score = fg.get("score", 50)
    if fg_score < 25:
        return -0.5, [f"시장 심리 극단공포 ({fg_score:.0f})"]
    if fg_score > 75:
        return -0.3, [f"시장 심리 극단탐욕 ({fg_score:.0f}) — 과열 경계"]
    if fg_score > 55:
        return 0.3, [f"시장 심리 탐욕 ({fg_score:.0f})"]
    return 0.0, []


def _scoreLiquidity(liquidity: dict) -> tuple[float, list[str]]:
    regime = liquidity.get("regime", "")
    if regime == "abundant":
        return 0.5, ["유동성 풍부"]
    if regime == "tight":
        return -0.5, ["유동성 긴축"]
    return 0.0, []


def _scoreForecast(forecast_result: dict | None) -> tuple[float, list[str]]:
    if not forecast_result:
        return 0.0, []
    contrib = 0.0
    reasons: list[str] = []
    rp = forecast_result.get("recessionProb")
    if rp and rp.get("probability") is not None:
        prob = rp["probability"]
        if prob > 0.4:
            contrib -= 0.5
            reasons.append(f"침체확률 {prob * 100:.0f}% — 경계")
        elif prob < 0.15:
            contrib += 0.3
            reasons.append(f"침체확률 {prob * 100:.0f}% — 낮음")
    lei = forecast_result.get("lei")
    if lei and isinstance(lei, dict):
        lei_signal = lei.get("signal")
        if lei_signal == "recession_warning":
            contrib -= 0.5
            reasons.append("LEI 침체 경고")
        elif lei_signal == "expansion":
            contrib += 0.3
            reasons.append("LEI 확장 지속")
    return contrib, reasons


def _scoreCrisis(crisis_result: dict | None) -> tuple[float, list[str]]:
    if not crisis_result:
        return 0.0, []
    cg = crisis_result.get("creditGap")
    if cg and cg.get("zone") in ("warning", "danger"):
        return -0.5, [f"Credit-to-GDP gap {cg.get('zoneLabel', '')}"]
    return 0.0, []


def _scoreInventory(inventory_result: dict | None) -> tuple[float, list[str]]:
    if not inventory_result:
        return 0.0, []
    ip = inventory_result.get("inventoryPhase")
    if not ip:
        return 0.0, []
    eq = ip.get("equityImplication")
    label = ip.get("phaseLabel", "")
    if eq == "bullish":
        return 0.3, [f"재고순환 {label} — 긍정"]
    if eq == "bearish":
        return -0.3, [f"재고순환 {label} — 부정"]
    return 0.0, []


def _scoreTrade(trade_result: dict | None, market: str) -> tuple[float, list[str]]:
    if not trade_result or market.upper() != "KR":
        return 0.0, []
    tot = trade_result.get("termsOfTrade")
    if not tot:
        return 0.0, []
    direction = tot.get("direction")
    if direction == "improving":
        return 0.3, ["교역조건 개선 — 수출 우호적"]
    if direction == "deteriorating":
        return -0.3, ["교역조건 악화 — 수출 부정적"]
    return 0.0, []


def _scoreCorporate(corporate_result: dict | None) -> tuple[float, list[str]]:
    if not corporate_result:
        return 0.0, []
    contrib = 0.0
    reasons: list[str] = []
    ec = corporate_result.get("earningsCycle")
    if ec and ec.get("currentDirection") == "contracting":
        contrib -= 0.3
        reasons.append(f"기업이익 수축 ({ec.get('currentLabel', '')})")
    elif ec and ec.get("currentDirection") == "expanding":
        contrib += 0.3
        reasons.append(f"기업이익 확장 ({ec.get('currentLabel', '')})")
    pr = corporate_result.get("ponziRatio")
    if pr and pr.get("currentRatio", 0) > 0.3:
        contrib -= 0.3
        reasons.append(f"Ponzi 비율 {pr.get('currentRatio', 0):.1%} — 금융 취약")
    return contrib, reasons


def _buildAllocation(
    overall: str, cycle: dict, sentiment: dict, liquidity: dict, crisis_result: dict | None
) -> dict | None:
    """포트폴리오 매핑 — regimeToAllocation → equity/bond/gold/cash 비중 dict."""
    try:
        from dartlab.core.finance.portfolioMapping import regimeToAllocation

        alloc = regimeToAllocation(
            {
                "overall": overall,
                "cycle": cycle,
                "sentiment": sentiment,
                "liquidity": liquidity
                if isinstance(liquidity, dict)
                else {"regime": liquidity.get("regime") if isinstance(liquidity, dict) else ""},
                "crisis": crisis_result,
            }
        )
        return {
            "equity": alloc.equity,
            "bond": alloc.bond,
            "gold": alloc.gold,
            "cash": alloc.cash,
            "regime": alloc.regime,
            "rationale": alloc.rationale,
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def _buildStrategiesDashboard(
    cycle,
    rates,
    assets,
    sentiment,
    liquidity,
    forecast_result,
    crisis_result,
    inventory_result,
    trade_result,
    corporate_result,
) -> dict | None:
    """40개 투자전략 대시보드 — evaluateStrategies → signals list."""
    try:
        from dartlab.core.finance.strategyRules import evaluateStrategies

        signals = evaluateStrategies(
            {
                "cycle": cycle,
                "rates": rates,
                "assets": assets,
                "sentiment": sentiment,
                "liquidity": liquidity,
                "forecast": forecast_result,
                "crisis": crisis_result,
                "inventory": inventory_result,
                "trade": trade_result,
                "corporate": corporate_result,
            }
        )
        return {
            "total": len(signals),
            "active": sum(1 for s in signals if s.active is True),
            "bullish": sum(1 for s in signals if s.active and s.direction == "bullish"),
            "bearish": sum(1 for s in signals if s.active and s.direction == "bearish"),
            "signals": [
                {
                    "id": s.id,
                    "name": s.name,
                    "active": s.active,
                    "direction": s.direction,
                    "strength": s.strength,
                    "confidence": s.confidence,
                    "description": s.description,
                }
                for s in signals
            ],
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def _addGrowthAtRisk(forecast_result: dict | None, liquidity: dict, as_of: str | None) -> None:
    """Adrian-Boyarchenko-Giannone (2019) FCI → GDP 분위회귀. forecast_result 에 in-place 추가."""
    if forecast_result is None:
        return
    try:
        from dartlab.macro._helpers import fetch_series_list, get_gather
        from dartlab.macro.growthAtRisk import growthAtRisk as _gar

        fci_data = liquidity.get("fci") if isinstance(liquidity, dict) else None
        fci_series = fci_data.get("history") if isinstance(fci_data, dict) else None

        _g = get_gather(as_of)
        gdp_series = fetch_series_list(_g, "GDP")
        if not (gdp_series and len(gdp_series) >= 20):
            return
        gdp_growth = [
            ((gdp_series[i] / gdp_series[i - 4]) - 1) * 100
            for i in range(4, len(gdp_series))
            if gdp_series[i - 4] and gdp_series[i - 4] > 0
        ]

        if not fci_series:
            nfci_series = fetch_series_list(_g, "NFCI")
            if nfci_series and len(nfci_series) >= 20:
                fci_series = nfci_series

        if fci_series and gdp_growth:
            gar = _gar(fci_series, gdp_growth, horizon=4)
            if gar:
                forecast_result["growthAtRisk"] = gar
    except (KeyError, ValueError, TypeError, AttributeError, ImportError):
        return


def analyze_summary(*, market: str = "US", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """매크로 전체 종합 판정 — **종목 분석 시 macro 호출은 이 함수 1회로 끝낸다**.

    11개 축(cycle, rates, assets, sentiment, liquidity, forecast, crisis,
    inventory, trade, corporate, scenario)을 독립 호출하여 종합 스코어와
    자산배분, 투자전략 대시보드를 산출한다.

    AI 사용 가이드:
        - 종목/회사 분석 컨텍스트에서는 **이 함수 1회**만 호출하라.
          단일 축(cycle/rates/liquidity 등) 11번 반복 호출 금지.
        - 결과 dict의 `cycle`, `rates`, `liquidity` 등 11축이 이미 포함됨.
        - 단일 축 호출은 사용자가 "금리만 자세히" 같이 명시했을 때만.
        - market은 종목의 currency에 맞게 — KR 종목은 "KR", US 종목은 "US".

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR"). 기본 "US".
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.
    overrides : dict | None
        AI 가정 교체. 전체 축에 전파.

    Returns
    -------
    dict
        market : str — 시장 코드
        overall : str — 종합 판정 ("favorable" | "neutral" | "unfavorable")
        overallLabel : str — 종합 판정 한글 ("우호적" | "중립" | "비우호적")
        score : float — 종합 스코어 (점, -4 ~ +4, 양수=우호적)
        contributions : dict[str, float] — 축별 기여도 (0이 아닌 축만)
        reasons : list[str] — 판정 근거 문장 리스트
        cycle : dict — 경기사이클 분석 결과
        rates : dict — 금리/채권 분석 결과
        assets : dict — 자산시장 분석 결과
        sentiment : dict — 시장 심리 분석 결과
        liquidity : dict — 유동성 분석 결과
        forecast : dict | None — 경제 예측 (LEI, 침체확률, Hamilton RS, Nowcast)
        crisis : dict | None — 위기 감지 (Credit Gap, GHS, Minsky, Dalio 등)
        inventory : dict | None — 재고순환 (ISM 바로미터, 재고 국면)
        trade : dict | None — 교역 분석 (교역조건, 대용치, 수출이익)
        corporate : dict | None — 기업집계 (이익사이클, Ponzi, 레버리지)
        allocation : dict | None — 자산배분 추천
            equity : float — 주식 비중 (%)
            bond : float — 채권 비중 (%)
            gold : float — 금 비중 (%)
            cash : float — 현금 비중 (%)
            regime : str — 레짐 코드
            rationale : str — 근거 해설
        strategies : dict | None — 투자전략 대시보드
            total : int — 전체 전략 수
            active : int — 활성 전략 수
            bullish : int — 강세 전략 수
            bearish : int — 약세 전략 수
            signals : list[dict] — 개별 전략 시그널
                id : int — 전략 번호
                name : str — 전략명
                active : bool — 활성 여부
                direction : str — 방향 ("bullish" | "bearish")
                strength : float — 강도 (0~1)
                confidence : float — 신뢰도 (0~1)
                description : str — 해설
    """
    from dartlab.macro.assets import analyze_assets
    from dartlab.macro.cycle import analyze_cycle
    from dartlab.macro.liquidity import calcLiquidity
    from dartlab.macro.rates import analyze_rates
    from dartlab.macro.sentiment import calcSentiment

    # as_of/overrides를 전체 축에 전파
    _ax = {"market": market, "as_of": as_of, "overrides": overrides}

    cycle = analyze_cycle(**_ax)
    rates = analyze_rates(**_ax)
    assets = analyze_assets(**_ax)
    sentiment = calcSentiment(**_ax)
    liquidity = calcLiquidity(**_ax)

    # 신규 축 (실패해도 종합 판정은 계속)
    forecast_result = None
    crisis_result = None
    inventory_result = None
    trade_result = None

    try:
        from dartlab.macro.forecast import analyze_forecast

        forecast_result = analyze_forecast(**_ax)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    try:
        from dartlab.macro.crisis import analyze_crisis

        # 다른 축 결과를 crisis에 전달
        crisis_kwargs: dict = {}
        if forecast_result:
            rp = forecast_result.get("recessionProb")
            if rp:
                crisis_kwargs["probitProb"] = rp.get("probability")
            lei = forecast_result.get("lei")
            if lei and isinstance(lei, dict) and "signal" in lei:
                crisis_kwargs["leiSignal"] = lei.get("signal")
        crisis_result = analyze_crisis(**_ax, **crisis_kwargs)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    try:
        from dartlab.macro.inventory import analyze_inventory

        inventory_result = analyze_inventory(**_ax)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    try:
        from dartlab.macro.trade import analyze_trade

        trade_result = analyze_trade(**_ax)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    corporate_result = None
    try:
        from dartlab.macro.corporate import analyze_corporate

        corporate_result = analyze_corporate(**_ax)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    score = 0.0
    reasons: list[str] = []
    contributions: dict[str, float] = {}

    # 9 축 scoring 을 sub 에 위임 — 각 sub 는 (contrib, reason_list) 리턴.
    for axisName, contrib, axReasons in (
        ("cycle", *_scoreCycle(cycle)),
        ("rates", *_scoreRates(rates)),
        ("sentiment", *_scoreSentiment(sentiment)),
        ("liquidity", *_scoreLiquidity(liquidity)),
        ("forecast", *_scoreForecast(forecast_result)),
        ("crisis", *_scoreCrisis(crisis_result)),
        ("inventory", *_scoreInventory(inventory_result)),
        ("trade", *_scoreTrade(trade_result, market)),
        ("corporate", *_scoreCorporate(corporate_result)),
    ):
        score += contrib
        contributions[axisName] = contrib
        reasons.extend(axReasons)

    # 종합 판정
    if score >= 1.0:
        overall = "favorable"
        overallLabel = "우호적"
    elif score <= -1.0:
        overall = "unfavorable"
        overallLabel = "비우호적"
    else:
        overall = "neutral"
        overallLabel = "중립"

    allocation_result = _buildAllocation(overall, cycle, sentiment, liquidity, crisis_result)
    strategies_result = _buildStrategiesDashboard(
        cycle,
        rates,
        assets,
        sentiment,
        liquidity,
        forecast_result,
        crisis_result,
        inventory_result,
        trade_result,
        corporate_result,
    )
    _addGrowthAtRisk(forecast_result, liquidity, as_of)

    return {
        "market": market.upper(),
        "overall": overall,
        "overallLabel": overallLabel,
        "score": round(score, 1),
        "contributions": {k: round(v, 2) for k, v in contributions.items() if v != 0},
        "reasons": reasons,
        "cycle": cycle,
        "rates": rates,
        "assets": assets,
        "sentiment": sentiment,
        "liquidity": liquidity,
        "forecast": forecast_result,
        "crisis": crisis_result,
        "inventory": inventory_result,
        "trade": trade_result,
        "corporate": corporate_result,
        "allocation": allocation_result,
        "strategies": strategies_result,
    }
