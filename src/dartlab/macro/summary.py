"""매크로 종합 분석 — 전체 축 종합 매트릭스."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def analyze_summary(*, market: str = "US", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """매크로 전체 종합 판정.

    11개 축(cycle, rates, assets, sentiment, liquidity, forecast, crisis,
    inventory, trade, corporate, scenario)을 독립 호출하여 종합 스코어와
    자산배분, 투자전략 대시보드를 산출한다.

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

    # 종합 판정 스코어 (-4 ~ +4, 양수=우호적)
    score = 0.0
    reasons: list[str] = []
    contributions: dict[str, float] = {}  # 축별 기여도

    # ── 기존 5축 ──

    # 사이클
    phase = cycle.get("phase", "")
    cycle_contrib = 0.0
    if phase in ("recovery", "expansion"):
        cycle_contrib = 1.0
        reasons.append(f"사이클 {cycle.get('phaseLabel', '')} — 우호적")
    elif phase == "contraction":
        cycle_contrib = -1.5
        reasons.append(f"사이클 {cycle.get('phaseLabel', '')} — 비우호적")
    elif phase == "slowdown":
        cycle_contrib = -0.5
        reasons.append(f"사이클 {cycle.get('phaseLabel', '')} — 주의")
    score += cycle_contrib
    contributions["cycle"] = cycle_contrib

    # 금리 방향
    rates_contrib = 0.0
    outlook = rates.get("outlook", {})
    direction = outlook.get("direction", "")
    if direction == "cut":
        rates_contrib = 0.5
        reasons.append("금리 인하 기대 — 유동성 우호적")
    elif direction == "hike":
        rates_contrib = -0.5
        reasons.append("금리 인상 가능 — 유동성 비우호적")
    score += rates_contrib
    contributions["rates"] = rates_contrib

    # 심리
    sentiment_contrib = 0.0
    fg = sentiment.get("fearGreed")
    if fg is not None:
        fg_score = fg.get("score", 50)
        if fg_score < 25:
            sentiment_contrib = -0.5
            reasons.append(f"시장 심리 극단공포 ({fg_score:.0f})")
        elif fg_score > 75:
            sentiment_contrib = -0.3
            reasons.append(f"시장 심리 극단탐욕 ({fg_score:.0f}) — 과열 경계")
        elif fg_score > 55:
            sentiment_contrib = 0.3
            reasons.append(f"시장 심리 탐욕 ({fg_score:.0f})")
    score += sentiment_contrib
    contributions["sentiment"] = sentiment_contrib

    # 유동성
    liquidity_contrib = 0.0
    liq_regime = liquidity.get("regime", "")
    if liq_regime == "abundant":
        liquidity_contrib = 0.5
        reasons.append("유동성 풍부")
    elif liq_regime == "tight":
        liquidity_contrib = -0.5
        reasons.append("유동성 긴축")
    score += liquidity_contrib
    contributions["liquidity"] = liquidity_contrib

    # ── 신규 축 ──

    # 예측
    forecast_contrib = 0.0
    if forecast_result:
        rp = forecast_result.get("recessionProb")
        if rp and rp.get("probability") is not None:
            prob = rp["probability"]
            if prob > 0.4:
                forecast_contrib -= 0.5
                reasons.append(f"침체확률 {prob * 100:.0f}% — 경계")
            elif prob < 0.15:
                forecast_contrib += 0.3
                reasons.append(f"침체확률 {prob * 100:.0f}% — 낮음")

        lei = forecast_result.get("lei")
        if lei and isinstance(lei, dict):
            lei_signal = lei.get("signal")
            if lei_signal == "recession_warning":
                forecast_contrib -= 0.5
                reasons.append("LEI 침체 경고")
            elif lei_signal == "expansion":
                forecast_contrib += 0.3
                reasons.append("LEI 확장 지속")
    score += forecast_contrib
    contributions["forecast"] = forecast_contrib

    # 위기
    crisis_contrib = 0.0
    if crisis_result:
        cg = crisis_result.get("creditGap")
        if cg and cg.get("zone") in ("warning", "danger"):
            crisis_contrib = -0.5
            reasons.append(f"Credit-to-GDP gap {cg.get('zoneLabel', '')}")
    score += crisis_contrib
    contributions["crisis"] = crisis_contrib

    # 재고
    inventory_contrib = 0.0
    if inventory_result:
        ip = inventory_result.get("inventoryPhase")
        if ip:
            eq = ip.get("equityImplication")
            if eq == "bullish":
                inventory_contrib = 0.3
                reasons.append(f"재고순환 {ip.get('phaseLabel', '')} — 긍정")
            elif eq == "bearish":
                inventory_contrib = -0.3
                reasons.append(f"재고순환 {ip.get('phaseLabel', '')} — 부정")
    score += inventory_contrib
    contributions["inventory"] = inventory_contrib

    # 교역 (KR만)
    trade_contrib = 0.0
    if trade_result and market.upper() == "KR":
        tot = trade_result.get("termsOfTrade")
        if tot:
            tot_dir = tot.get("direction")
            if tot_dir == "improving":
                trade_contrib = 0.3
                reasons.append("교역조건 개선 — 수출 우호적")
            elif tot_dir == "deteriorating":
                trade_contrib = -0.3
                reasons.append("교역조건 악화 — 수출 부정적")
    score += trade_contrib
    contributions["trade"] = trade_contrib

    # 기업집계
    corporate_contrib = 0.0
    if corporate_result:
        ec = corporate_result.get("earningsCycle")
        if ec and ec.get("currentDirection") == "contracting":
            corporate_contrib -= 0.3
            reasons.append(f"기업이익 수축 ({ec.get('currentLabel', '')})")
        elif ec and ec.get("currentDirection") == "expanding":
            corporate_contrib += 0.3
            reasons.append(f"기업이익 확장 ({ec.get('currentLabel', '')})")

        pr = corporate_result.get("ponziRatio")
        if pr and pr.get("currentRatio", 0) > 0.3:
            corporate_contrib -= 0.3
            reasons.append(f"Ponzi 비율 {pr.get('currentRatio', 0):.1%} — 금융 취약")
    score += corporate_contrib
    contributions["corporate"] = corporate_contrib

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

    # ── 포트폴리오 매핑 ──
    allocation_result = None
    try:
        from dartlab.core.finance.portfolioMapping import regimeToAllocation

        alloc_input = {
            "overall": overall,
            "cycle": cycle,
            "sentiment": sentiment,
            "liquidity": liquidity
            if isinstance(liquidity, dict)
            else {"regime": liquidity.get("regime") if isinstance(liquidity, dict) else ""},
            "crisis": crisis_result,
        }
        alloc = regimeToAllocation(alloc_input)
        allocation_result = {
            "equity": alloc.equity,
            "bond": alloc.bond,
            "gold": alloc.gold,
            "cash": alloc.cash,
            "regime": alloc.regime,
            "rationale": alloc.rationale,
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # ── 40개 투자전략 대시보드 ──
    strategies_result = None
    try:
        from dartlab.core.finance.strategyRules import evaluateStrategies

        macro_data = {
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
        signals = evaluateStrategies(macro_data)
        active_count = sum(1 for s in signals if s.active is True)
        bullish_count = sum(1 for s in signals if s.active and s.direction == "bullish")
        bearish_count = sum(1 for s in signals if s.active and s.direction == "bearish")
        strategies_result = {
            "total": len(signals),
            "active": active_count,
            "bullish": bullish_count,
            "bearish": bearish_count,
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
        pass

    # ── Growth-at-Risk — Adrian, Boyarchenko, Giannone (2019) AER ──
    # FCI → GDP 성장률 조건부 분위 추정 (summary 단계에서 축간 데이터 공유)
    if forecast_result is not None:
        try:
            from dartlab.core.finance.growthAtRisk import growthAtRisk as _gar

            fci_data = liquidity.get("fci") if isinstance(liquidity, dict) else None
            fci_series = fci_data.get("history") if isinstance(fci_data, dict) else None
            # fci_series가 없으면 단일 값으로는 분위회귀 불가 — skip
            # GDP 성장률 시계열
            from dartlab.macro._helpers import fetch_series_list, get_gather

            _g = get_gather(as_of)
            gdp_series = fetch_series_list(_g, "GDP")
            if gdp_series and len(gdp_series) >= 20:
                # GDP → YoY 성장률
                gdp_growth = []
                for i in range(4, len(gdp_series)):
                    prev = gdp_series[i - 4]
                    if prev and prev > 0:
                        gdp_growth.append(((gdp_series[i] / prev) - 1) * 100)

                # FCI 시계열 — liquidity에 history가 없으면 FCI 값 시계열 구축 시도
                if not fci_series:
                    # 단순 근사: NFCI 시계열을 FCI proxy로 사용
                    nfci_series = fetch_series_list(_g, "NFCI")
                    if nfci_series and len(nfci_series) >= 20:
                        fci_series = nfci_series

                if fci_series and gdp_growth:
                    gar = _gar(fci_series, gdp_growth, horizon=4)
                    if gar:
                        forecast_result["growthAtRisk"] = gar
        except (KeyError, ValueError, TypeError, AttributeError, ImportError):
            pass

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
