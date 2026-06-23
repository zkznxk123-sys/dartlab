"""story 블록 빌더 — macro 도메인 (debt-honesty P3-3 god-split). 공유 imports·상수·헬퍼는 _shared."""

from __future__ import annotations

from dartlab.story.builders._shared import (
    FlagBlock,
    HeadingBlock,
    MetricBlock,
    TextBlock,
    _meta,
)

# ── 매크로 블록 ──


def macroPositionBlock(data: dict) -> list:
    """calcMacroEnvironment 결과 → 경제 사이클 + 기업 포지션."""
    if not data:
        return []

    phase_label = data.get("phaseLabel", "미정")
    confidence = data.get("confidence", "low")
    position_label = data.get("positionLabel", "중립")
    cyclicality = data.get("cyclicality", "moderate")
    signals = data.get("signals", [])

    metrics = [
        ("경제 국면", f"{phase_label} ({confidence})"),
        ("업종 경기민감도", cyclicality),
        ("현재 포지션", position_label),
    ]

    blocks: list = [
        HeadingBlock(
            _meta("macroEnvironment").label,
            level=2,
            helper="경제 사이클 4국면(침체/회복/확장/둔화) 판별 + 업종별 투자 전략",
        ),
        MetricBlock(metrics),
    ]

    if signals:
        blocks.append(TextBlock("판별 근거: " + " | ".join(signals[:4])))

    implication = data.get("implication")
    if implication:
        blocks.append(TextBlock(f"시사점: {implication}"))

    return blocks


def macroEnvironmentBlock(summary: dict) -> list:
    """macro 종합 결과 → 경제 환경 신호등."""
    if not summary:
        return []

    overall_label = summary.get("overallLabel", "")
    score = summary.get("score", 0)
    reasons = summary.get("reasons", []) or []
    contributions = summary.get("contributions", {}) or {}
    allocation = summary.get("allocation") or {}

    if not overall_label:
        return []

    metrics = [
        ("종합 판정", f"{overall_label} (score {score:+.1f})"),
    ]
    if reasons:
        metrics.append(("핵심 근거", ", ".join(reasons[:3])))

    contrib_parts = []
    for axis, val in sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True):
        if val != 0:
            contrib_parts.append(f"{axis} {val:+.1f}")
    if contrib_parts:
        metrics.append(("축별 기여", ", ".join(contrib_parts[:5])))

    if allocation:
        eq = allocation.get("equity", 0)
        bd = allocation.get("bond", 0)
        gd = allocation.get("gold", 0)
        cs = allocation.get("cash", 0)
        metrics.append(("자산배분", f"주식 {eq}% / 채권 {bd}% / 금 {gd}% / 현금 {cs}%"))
        regime = allocation.get("regime", "")
        if regime:
            metrics.append(("투자 국면", regime))

    from dartlab.story.narrate import narrateMacroEnvironment

    blocks: list = [
        HeadingBlock(
            _meta("macroEnvironment").label,
            level=2,
            helper="매크로 11축 종합 판정 — 경제 환경이 투자에 우호적인가",
        ),
        MetricBlock(metrics),
    ]
    narrative = narrateMacroEnvironment(summary)
    if narrative:
        blocks.append(TextBlock(narrative))
    return blocks


def macroCycleBlock(data: dict) -> list:
    """dartlab.macro("사이클") 결과 → 경기 사이클 + 전환 시퀀스 + 섹터 전략."""
    if not data:
        return []

    phase = data.get("phase", "")
    phase_label = data.get("phaseLabel", "")
    confidence = data.get("confidence", "")
    signals = data.get("signals", []) or []
    sector_strategy = data.get("sectorStrategy", {}) or {}
    transition = data.get("transition") or {}

    if not phase:
        return []

    metrics = [
        ("경기 국면", f"{phase_label or phase}"),
        ("판정 신뢰도", confidence or "?"),
    ]
    if signals:
        metrics.append(("핵심 신호", ", ".join(signals[:3])))

    if transition:
        t_from = transition.get("from", "")
        t_to = transition.get("to", "")
        progress = transition.get("progress")
        if t_from and t_to:
            prog_str = f" ({progress:.0%})" if isinstance(progress, (int, float)) else ""
            metrics.append(("전환 시퀀스", f"{t_from} → {t_to}{prog_str}"))
        triggered = transition.get("triggered", [])
        pending = transition.get("pending", [])
        if triggered:
            metrics.append(("확인된 신호", ", ".join(triggered[:3])))
        if pending:
            metrics.append(("대기 신호", ", ".join(pending[:3])))

    sector_lines = []
    for k_label, k in [
        ("경기민감 (high)", "high"),
        ("중간민감 (moderate)", "moderate"),
        ("방어주 (defensive)", "defensive"),
        ("저민감 (low)", "low"),
    ]:
        v = sector_strategy.get(k)
        if v:
            sector_lines.append((k_label, v))

    blocks: list = [
        HeadingBlock(
            _meta("macroCycle").label,
            level=2,
            helper="회복/확장/둔화/침체 4국면 + 전환 시퀀스 + 섹터별 전략",
        ),
        MetricBlock(metrics),
    ]
    if sector_lines:
        blocks.append(MetricBlock(sector_lines))

    # Bridgewater 4 Quadrant (Growth × Inflation)
    quadrant = data.get("quadrant")
    if isinstance(quadrant, dict):
        q_label = quadrant.get("quadrantLabel", "")
        q_growth = "성장↑" if quadrant.get("growth") == "rising" else "성장↓"
        q_infl = "인플레↑" if quadrant.get("inflation") == "rising" else "인플레↓"
        q_conf = quadrant.get("confidence", "")
        q_lines = [
            ("매크로 체제", f"{q_label} ({q_growth}, {q_infl})"),
            ("체제 신뢰도", q_conf),
        ]
        asset_impl = quadrant.get("assetImplication", {})
        if asset_impl:
            ow = [k for k, v in asset_impl.items() if v == "overweight"]
            uw = [k for k, v in asset_impl.items() if v == "underweight"]
            if ow:
                q_lines.append(("Overweight", ", ".join(ow)))
            if uw:
                q_lines.append(("Underweight", ", ".join(uw)))
        blocks.append(MetricBlock(q_lines))

    return blocks


def macroRatesBlock(data: dict) -> list:
    """macro 금리 결과 → 금리 환경."""
    if not data:
        return []

    outlook = data.get("outlook") or {}
    expectation = data.get("expectation") or {}
    yield_curve = data.get("yieldCurve") or {}
    realRate = data.get("realRateRegime", "")

    direction = outlook.get("direction", "")
    if not direction:
        return []

    _DIR_LABELS = {"cut": "인하 기대", "hold": "동결", "hike": "인상 가능"}
    metrics: list[tuple[str, str]] = [
        ("금리 방향", _DIR_LABELS.get(direction, direction)),
    ]

    spread_2y_ff = expectation.get("spread2yFf")
    if spread_2y_ff is not None:
        metrics.append(("2Y-FF 스프레드", f"{spread_2y_ff:+.2f}%p"))

    slope = yield_curve.get("slope")
    if slope is not None:
        shape = "정상" if slope > 0 else "역전"
        metrics.append(("수익률곡선", f"{shape} (Slope {slope:+.2f}%p)"))

    if realRate:
        if isinstance(realRate, dict):
            metrics.append(("실질금리 국면", realRate.get("regimeLabel", "")))
        else:
            metrics.append(("실질금리 국면", str(realRate)))

    # ACM Term Premium
    tp = data.get("termPremium")
    if isinstance(tp, dict):
        tp_val = tp.get("value")
        tp_label = tp.get("zoneLabel", "")
        if tp_val is not None:
            metrics.append(("텀프리미엄", f"{tp_val:+.2f}%p ({tp_label})"))

    # Cochrane-Piazzesi Bond Risk Premium
    cp = data.get("bondRiskPremium")
    if isinstance(cp, dict):
        cp_val = cp.get("cpFactor")
        cp_label = cp.get("zoneLabel", "")
        if cp_val is not None:
            metrics.append(("CP 팩터", f"{cp_val:+.2f} ({cp_label})"))

    return [
        HeadingBlock(
            _meta("macroRates").label,
            level=2,
            helper="금리 방향 + 수익률곡선 + 텀프리미엄 + 채권 리스크프리미엄",
        ),
        MetricBlock(metrics),
    ]


def macroSentimentBlock(data: dict) -> list:
    """macro 심리 결과 → 시장 심리."""
    if not data:
        return []

    fg = data.get("fearGreed") or {}
    vix = data.get("vixRegime") or {}

    fg_score = fg.get("score")
    if fg_score is None:
        return []

    fg_label = fg.get("label", "")
    metrics: list[tuple[str, str]] = [
        ("공포탐욕", f"{fg_score:.0f} ({fg_label})"),
    ]

    vix_level = vix.get("level", "")
    vix_value = vix.get("value")
    if vix_level:
        vix_str = f"{vix_level}"
        if vix_value is not None:
            vix_str += f" ({vix_value:.1f})"
        metrics.append(("VIX 구간", vix_str))

    buy_signal = vix.get("buySignal")
    if buy_signal is not None:
        _BUY_LABELS = {0: "대기", 1: "1차 매수", 2: "2차 매수", 3: "3차 매수"}
        metrics.append(("분할매수 신호", f"{buy_signal}차 ({_BUY_LABELS.get(buy_signal, '')})"))

    # JLN Macro Uncertainty
    mu = data.get("macroUncertainty")
    if isinstance(mu, dict):
        mu_val = mu.get("value")
        mu_label = mu.get("zoneLabel", "")
        vs_vix = mu.get("vsVix", "")
        if mu_val is not None:
            metrics.append(("실물 불확실성", f"{mu_val:.3f} ({mu_label})"))
            if vs_vix == "divergent":
                metrics.append(("VIX-JLN 괴리", "금융과 실물 불확실성 방향 다름"))

    return [
        HeadingBlock(
            _meta("macroSentiment").label,
            level=2,
            helper="공포탐욕 + VIX + JLN 실물 불확실성 — 극단값에서 역투자 기회",
        ),
        MetricBlock(metrics),
    ]


def macroForecastBlock(data: dict | None) -> list:
    """macro 예측 결과 → 경기 전망."""
    if not data:
        return []

    metrics: list[tuple[str, str]] = []

    rp = data.get("recessionProb")
    if rp and rp.get("probability") is not None:
        prob = rp["probability"]
        if prob > 0.4:
            label = "경계"
        elif prob > 0.2:
            label = "주의"
        elif prob > 0.1:
            label = "보통"
        else:
            label = "낮음"
        metrics.append(("침체확률", f"{prob * 100:.0f}% ({label})"))

    lei = data.get("lei")
    if isinstance(lei, dict):
        signal = lei.get("signal", "")
        _LEI_LABELS = {
            "expansion": "확장 지속",
            "caution": "주의",
            "recession_warning": "침체 경고",
        }
        if signal:
            metrics.append(("LEI 신호", _LEI_LABELS.get(signal, signal)))

    sahm = data.get("sahmRule")
    if isinstance(sahm, dict):
        val = sahm.get("value")
        triggered = sahm.get("triggered", False)
        if val is not None:
            status = "트리거" if triggered else "정상"
            metrics.append(("Sahm Rule", f"{val:.2f}%p ({status})"))

    momentum = data.get("momentumSignal")
    if isinstance(momentum, dict):
        direction = momentum.get("direction", "")
        if direction:
            metrics.append(("성장 모멘텀", direction))

    # Growth-at-Risk (Adrian 2019)
    gar = data.get("growthAtRisk")
    if isinstance(gar, dict):
        gar5 = gar.get("currentGaR5")
        median = gar.get("median")
        tail = gar.get("tailRiskLabel", "")
        if gar5 is not None:
            metrics.append(("GaR 5th", f"{gar5:+.1f}% ({tail})"))
        if median is not None:
            metrics.append(("GaR 중위", f"{median:+.1f}%"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("macroForecast").label,
            level=2,
            helper="침체확률 + LEI + Sahm + Growth-at-Risk → 경기 방향 선행 지표",
        ),
        MetricBlock(metrics),
    ]


def macroCorporateBlock(data: dict | None) -> list:
    """macro 기업집계 결과 → 시장 전체 이익사이클."""
    if not data:
        return []

    metrics: list[tuple[str, str]] = []

    ec = data.get("earningsCycle")
    if ec:
        direction = ec.get("currentDirection", "")
        label = ec.get("currentLabel", direction)
        yoy = ec.get("latestYoY")
        yoy_str = f" (YoY {yoy:+.1f}%)" if yoy is not None else ""
        if label:
            metrics.append(("이익사이클", f"{label}{yoy_str}"))

    pr = data.get("ponziRatio")
    if pr:
        ratio = pr.get("currentRatio")
        if ratio is not None:
            metrics.append(("Ponzi 비율", f"{ratio:.1%} (ICR<1 기업 비중)"))

    lc = data.get("leverageCycle")
    if lc:
        median = lc.get("currentMedian")
        if median is not None:
            metrics.append(("레버리지 중간값", f"{median:.1f}%"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("macroCorporate").label,
            level=2,
            helper="전종목 재무제표 집계 — 시장 전체의 이익 건강도",
        ),
        MetricBlock(metrics),
    ]


def macroTradeBlock(data: dict | None) -> list:
    """macro 교역 결과 → 교역조건 (KR만)."""
    if not data:
        return []

    metrics: list[tuple[str, str]] = []

    tot = data.get("termsOfTrade")
    if tot:
        direction = tot.get("direction", "")
        _DIR_LABELS = {"improving": "개선", "stable": "안정", "deteriorating": "악화"}
        if direction:
            metrics.append(("교역조건", _DIR_LABELS.get(direction, direction)))

    ep = data.get("exportProfit")
    if isinstance(ep, dict):
        signal = ep.get("signal", "")
        if signal:
            metrics.append(("수출이익 함의", signal))

    lrs = data.get("leadingRelativeStrength")
    if isinstance(lrs, dict):
        direction = lrs.get("direction", "")
        if direction:
            metrics.append(("양국 선행지수", direction))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("macroTrade").label,
            level=2,
            helper="교역조건 + 수출이익 선행 — 한국 수출기업 영향",
        ),
        MetricBlock(metrics),
    ]


def macroFlagsBlock(summary: dict) -> list:
    """macro 종합에서 경고/기회 플래그 집계."""
    if not summary:
        return []

    warnings: list[str] = []
    opportunities: list[str] = []

    crisis = summary.get("crisis")
    if isinstance(crisis, dict):
        cg = crisis.get("creditGap")
        if cg and cg.get("zone") in ("warning", "danger"):
            warnings.append(f"Credit-to-GDP gap {cg.get('zoneLabel', '경계')}")
        ghs = crisis.get("ghsScore")
        if isinstance(ghs, dict) and ghs.get("score", 0) > 50:
            warnings.append(f"GHS 위기 점수 {ghs['score']:.0f}")
        minsky = crisis.get("minskyPhase")
        if isinstance(minsky, dict) and minsky.get("phase") in ("overtrading", "discredit", "revulsion"):
            warnings.append(f"Minsky {minsky.get('phaseLabel', minsky['phase'])}")
        # Excess Bond Premium (Gilchrist 2012)
        ebp = crisis.get("excessBondPremium")
        if isinstance(ebp, dict) and ebp.get("recessionSignal"):
            warnings.append(f"EBP {ebp.get('ebp', 0):.2f} — 침체 12개월 신호")
        elif isinstance(ebp, dict) and ebp.get("zone") == "stress":
            warnings.append(f"EBP {ebp.get('ebp', 0):.2f} — 신용 스트레스")
        # Verdad Credit Cycle
        cc = crisis.get("creditCycle")
        if isinstance(cc, dict):
            cc_phase = cc.get("phase")
            if cc_phase == "trough":
                opportunities.append("신용사이클 저점 — 역발상 매수 기회")
            elif cc_phase == "peak":
                warnings.append("신용사이클 정점 — 리스크 축소 시작")

    corporate = summary.get("corporate")
    if isinstance(corporate, dict):
        pr = corporate.get("ponziRatio")
        if pr and pr.get("currentRatio", 0) > 0.3:
            warnings.append(f"Ponzi비율 {pr['currentRatio']:.0%} — 금융 취약")

    sentiment = summary.get("sentiment")
    if isinstance(sentiment, dict):
        fg = sentiment.get("fearGreed")
        if fg and fg.get("score") is not None:
            s = fg["score"]
            if s < 25:
                opportunities.append(f"극단공포 ({s:.0f}) — 역투자 기회")
            elif s > 75:
                warnings.append(f"극단탐욕 ({s:.0f}) — 과열 경계")

    forecast = summary.get("forecast")
    if isinstance(forecast, dict):
        rp = forecast.get("recessionProb")
        if rp and rp.get("probability", 0) > 0.3:
            warnings.append(f"침체확률 {rp['probability'] * 100:.0f}%")

    overall = summary.get("overall", "")
    score = summary.get("score", 0)
    if overall == "favorable" and score >= 2.0:
        cycle = summary.get("cycle", {})
        phase = cycle.get("phaseLabel", "")
        opportunities.append(f"사이클 {phase} + 종합 우호 — 위험자산 긍정")

    if not warnings and not opportunities:
        return []

    blocks: list = []
    if warnings:
        blocks.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        blocks.append(FlagBlock(opportunities, kind="opportunity"))
    return blocks
