"""Analysis Override 표준 — AI/사용자가 분석 가정을 조율하는 인터페이스.

Level 1 (시스템 디폴트): overrides=None → 자동 계산
Level 2 (AI/사용자 조율): overrides={...} → 지정 가정만 교체, 나머지 자동

4개 엔진(analysis/credit/quant/macro) 전부 동일 패턴.
AI 는 엔진 결과의 소비자가 아니라 조율자 — 가정이 비현실적이면 이 인터페이스로 교체.
"""

from __future__ import annotations

from typing import Any

# ── Override 키 정의 (엔진별 그룹) ──

FORECAST_KEYS = {
    "baseRevenue",  # float — 기준 매출 (원). None이면 자동 (TTM 또는 mid-cycle)
    "growthRates",  # list[float] — 연도별 매출 성장률 (%). None이면 forecast 엔진 자동
    "opm",  # float — 영업이익률 (0.0~1.0). None이면 과거 추세
    "capexRatio",  # float — CAPEX/매출 (0.0~1.0). None이면 과거 평균
    "depreciationRatio",  # float — 감가상각/매출
    "nwcRatio",  # float — 운전자본/매출
    "taxRate",  # float — 유효세율
    "marginPath",  # list[float] — 연도별 영업마진 (%) — Phase 3 multi-stage
    "reinvestmentPath",  # list[float] — 연도별 재투자율 (%) — Phase 3 multi-stage
}

VALUATION_KEYS = {
    "wacc",  # float — WACC (%). None이면 CAPM 자동
    "terminalGrowth",  # float — 영구성장률 (%). None이면 업종/생애주기 기본
    "primaryModel",  # str — "dcf"/"rim"/"ddm"/"relative"/"dcf2stage"/"liquidation"/"relativeSurvival"
    "riskFreeRate",  # float — 무위험수익률 (%)
    "equityRiskPremium",  # float — 시장 리스크 프리미엄 (%)
    "beta",  # float — beta 계수
    # ── Damodaran 흡수 (Phase 1+2) ──
    "countryCode",  # str — ISO2 (KR/US/JP/...). currency 에서 자동 추론
    "countryRiskPremium",  # float — 국가 리스크 프리미엄 (%). Damodaran 테이블 override
    "lifeCyclePhase",  # str — "earlyGrowth"/"highGrowth"/"matureGrowth"/"matureStable"/"decline"/"turnaround"
    "pSurvival",  # float — 0.0~1.0. Dark Side of Valuation going-concern 가중치
    "liquidationValue",  # float — 명시적 청산가치 (원). None 이면 자본×(1-discount)
    "liquidationDiscount",  # float — 0.0~0.7. book equity 대비 청산 할인
    # ── Damodaran Phase 3 ──
    "impliedERP",  # bool — True 면 Gordon 역산 ERP 사용 (시장 내재). 실패 시 fallback.
    "bottomUpBeta",  # bool — True 면 섹터 peer unlever/relever Hamada 적용.
    "optimalROIC",  # float — Control Value 계산용 최적 ROIC (%)
    "synergyType",  # str — "cost"/"revenue"/"financial" (M&A 시나리오)
    "controlScenario",  # str — "statusQuo"/"restructured"/"merged" (M&A 시나리오)
}

# Phase 3 FORECAST 확장 (가변 마진/재투자율)
_PHASE3_FORECAST_KEYS = {
    "marginPath",  # list[float] — 연도별 영업마진 (%)
    "reinvestmentPath",  # list[float] — 연도별 재투자율 (%)
}

ANALYSIS_KEYS = {
    "peerGroup",  # list[str] — 비교 피어 종목코드 리스트
    "periodRange",  # tuple[str, str] — 분석 기간 (예: ("2020","2024"))
    "sectorBench",  # str — 섹터 벤치마크 override
}

CREDIT_KEYS = {
    "debtRatio",  # float — 시나리오 부채비율 (%)
    "interestCoverage",  # float — 시나리오 이자보상배율
    "currentRatio",  # float — 유동비율
    "quickRatio",  # float — 당좌비율
    "ocfToDebt",  # float — 영업CF/부채
    "fcfToDebt",  # float — FCF/부채
    "scenarioStress",  # str — "mild"/"moderate"/"severe" 스트레스 시나리오
}

QUANT_KEYS = {
    "window",  # int — 이동평균/RSI 등 창 크기
    "threshold",  # float — 신호 임계값
    "period",  # str — 분석 기간 (예: "1y", "6m")
    "benchmark",  # str — 벤치마크 (예: "KOSPI", "SPX")
}

MACRO_KEYS = {
    "cyclePhase",  # str — 사이클 국면 override ("expansion"/"peak"/"contraction"/"trough")
    "rateScenario",  # str — 금리 시나리오 ("hike"/"hold"/"cut")
    "fxScenario",  # str — 환율 시나리오
    "liquidityScenario",  # str — 유동성 시나리오
}

# 엔진별 override 허용 키 집합
ENGINE_KEYS: dict[str, set[str]] = {
    "analysis": FORECAST_KEYS | VALUATION_KEYS | ANALYSIS_KEYS,
    "credit": CREDIT_KEYS,
    "quant": QUANT_KEYS,
    "macro": MACRO_KEYS,
}

ALL_KEYS = FORECAST_KEYS | VALUATION_KEYS | ANALYSIS_KEYS | CREDIT_KEYS | QUANT_KEYS | MACRO_KEYS


# ── Assumption 수집 (4 엔진 공통) ─────────────────────────
#
# AI 가 tool_result 에서 "엔진이 어떤 가정을 썼나" 즉시 인지 → override 재호출.
# 각 calc 결과의 알려진 alias 를 표준 키 (ALL_KEYS) 로 정규화.

_ASSUMPTION_ALIASES: dict[str, str] = {
    # VALUATION (discountRate/baseWacc/... → wacc)
    "discountRate": "wacc",
    "baseWacc": "wacc",
    "assumedWacc": "wacc",
    "terminalGrowth": "terminalGrowth",
    "baseTerminalGrowth": "terminalGrowth",
    "growthRateInitial": "growthRates",
    # FORECAST
    "baseRevenue": "baseRevenue",
    "projectedGrowth": "growthRates",
    "projectedOpm": "opm",
    "assumedMargin": "opm",
    "opm": "opm",
    "capexRatio": "capexRatio",
    "depreciationRatio": "depreciationRatio",
    "nwcRatio": "nwcRatio",
    "taxRate": "taxRate",
    # CREDIT
    "debtRatio": "debtRatio",
    "interestCoverage": "interestCoverage",
    "currentRatio": "currentRatio",
    "quickRatio": "quickRatio",
    "ocfToDebt": "ocfToDebt",
    "fcfToDebt": "fcfToDebt",
    # Damodaran Phase 1/2/3 (이름 = 표준 키 그대로)
    "countryCode": "countryCode",
    "countryRiskPremium": "countryRiskPremium",
    "lifeCyclePhase": "lifeCyclePhase",
    "pSurvival": "pSurvival",
    "liquidationValue": "liquidationValue",
    "liquidationDiscount": "liquidationDiscount",
    "impliedERP": "impliedERP",
    "historicalERP": "historicalERP",
    "bottomUpBeta": "bottomUpBeta",
    "peerCount": "peerCount",
    "optimalROIC": "optimalROIC",
    "synergyType": "synergyType",
    "controlScenario": "controlScenario",
    "controlPremium": "controlPremium",
    "synergy": "synergy",
    "standaloneValue": "standaloneValue",
    "revenueCAGR": "revenueCAGR",
    # MACRO (phase → cyclePhase)
    "phase": "cyclePhase",
    "confidence": "confidence",
    # QUANT (kwargs 에 넘어온 값 자체)
    "window": "window",
    "threshold": "threshold",
    "period": "period",
    "benchmark": "benchmark",
}


def buildAssumptions(
    results: Any,
    *,
    engine: str = "analysis",
    overrides: dict | None = None,
) -> dict:
    """엔진 결과에서 가정값을 표준 override 키로 수집. 4 엔진 공통.

    Args:
        results: analysis dict[blockKey → calc dict] · credit dict · macro dict · quant dict
        engine: analysis / credit / macro / quant (엔진별 특수 추출 분기)
        overrides: 이번 호출에 적용된 override (있으면 _overridden 에 명시)

    Returns:
        표준 키 dict + `_overridden` + `_flags` (detectExtremeFlags).
        빈 결과면 {} 반환.
    """
    collected: dict = {}
    container = results if isinstance(results, dict) else {}

    # 1. alias 평탄 수집 — analysis 는 nested blockKey, credit/macro 는 top-level
    # analysis: {"dcfValuation": {"discountRate": 10.4, ...}, ...}
    # credit: {"grade": "AA-", "metrics": {...}}
    # macro: {"phase": "recovery", "confidence": "high"}
    _scanForAliases(container, collected)
    for block in container.values():
        _scanForAliases(block, collected)

    # 2. 엔진별 특수 추출
    if engine == "analysis":
        _extractAnalysisSpecific(container, collected)
    elif engine == "credit":
        _extractCreditSpecific(container, collected)
    # macro/quant 는 alias 수집만으로 충분

    # 3. override 적용 표시
    collected["_overridden"] = sorted(overrides.keys()) if overrides else []

    # 4. flag 자가 의심
    flags = detectExtremeFlags(collected)
    if flags:
        collected["_flags"] = flags

    # 비어있으면 생략 (표준 키 0개 + flag 0)
    if len(collected) == 1 and collected["_overridden"] == [] and "_flags" not in collected:
        return {}
    return collected


def _scanForAliases(block: Any, collected: dict) -> None:
    """dict 에서 _ASSUMPTION_ALIASES 매칭 평탄 수집. 이미 있는 키는 skip (선점)."""
    if not isinstance(block, dict):
        return
    for rawKey, stdKey in _ASSUMPTION_ALIASES.items():
        if rawKey not in block or stdKey in collected:
            continue
        val = block[rawKey]
        if val is None:
            continue
        # 숫자/문자열/bool 기본, list 는 성장률/경로 키만
        if isinstance(val, (int, float, str, bool)):
            collected[stdKey] = val
        elif isinstance(val, (list, tuple)) and stdKey in ("growthRates", "marginPath", "reinvestmentPath"):
            collected[stdKey] = list(val)


def _extractAnalysisSpecific(results: dict, collected: dict) -> None:
    # primaryModel 추론 — valuationSynthesis.modelWeights 최대
    synth = results.get("valuationSynthesis")
    if isinstance(synth, dict):
        weights = synth.get("modelWeights")
        if isinstance(weights, dict) and weights:
            top = max(weights.items(), key=lambda kv: kv[1] if isinstance(kv[1], (int, float)) else 0)
            if isinstance(top[1], (int, float)) and top[1] > 0:
                collected.setdefault("primaryModel", top[0])
    # Kd/Ke/Beta — priceTarget.waccDetails (DCF 내부 가정)
    pt = results.get("priceTarget")
    if isinstance(pt, dict):
        wd = pt.get("waccDetails")
        if isinstance(wd, dict):
            for k in ("kd", "ke", "beta"):
                v = wd.get(k)
                if isinstance(v, (int, float)):
                    collected.setdefault(k, v)


def _extractCreditSpecific(result: dict, collected: dict) -> None:
    # 최상위 등급/점수
    for k in ("grade", "score", "sector"):
        if k in result and k not in collected:
            collected[k] = result[k]
    # axis 결과면 metrics 에서 표준 키 추출
    metrics = result.get("metrics") or {}
    if not isinstance(metrics, dict):
        return
    for stdKey, candidates in (
        ("debtRatio", ("debtRatio", "debtToEquity", "leverage")),
        ("interestCoverage", ("interestCoverage", "icr")),
        ("currentRatio", ("currentRatio",)),
        ("quickRatio", ("quickRatio",)),
        ("ocfToDebt", ("ocfToDebt",)),
        ("fcfToDebt", ("fcfToDebt",)),
    ):
        if stdKey in collected:
            continue
        for c in candidates:
            m = metrics.get(c)
            if isinstance(m, dict) and "value" in m:
                collected[stdKey] = m["value"]
                break
            if isinstance(m, (int, float)):
                collected[stdKey] = m
                break


def validateOverrides(overrides: dict | None, engine: str | None = None) -> dict:
    """override dict 검증 + 정규화. 잘못된 키는 경고 후 무시.

    Args:
        overrides: AI/사용자가 넘긴 override dict
        engine: "analysis"/"credit"/"quant"/"macro". 지정 시 해당 엔진 허용 키만 통과.
                None 이면 ALL_KEYS 전체 통과.
    """
    if not overrides:
        return {}

    allowed = ENGINE_KEYS.get(engine, ALL_KEYS) if engine else ALL_KEYS

    clean: dict = {}
    for key, value in overrides.items():
        if key not in allowed:
            continue  # 미인식/엔진 범위 밖 키 무시
        if value is None:
            continue  # None은 "자동"과 동일
        clean[key] = value

    return clean


def applyOverride(auto_value: Any, override_key: str, overrides: dict) -> Any:
    """자동 계산 값에 override 적용. override 없으면 auto_value 반환."""
    if not overrides or override_key not in overrides:
        return auto_value
    return overrides[override_key]


def detectExtremeFlags(assumptions: dict | None) -> list[dict]:
    """assumptions 값을 룰 기반으로 검사 → "의심스럽다 + 재호출 권고" flag 리스트.

    엔진 자가 의심 매커니즘. AI 가 판단하기 전에 엔진이 먼저 "이 가정은 비정상" 이라고
    말한다. 각 flag 에는 `suggestedRetry` (override 재호출 dict) 가 동봉되어 AI 가
    복사 수준으로 실행할 수 있다.
    """
    if not assumptions or not isinstance(assumptions, dict):
        return []

    flags: list[dict] = []

    # WACC 범위 검사 (한국 주식 일반적 8~12% 기준)
    wacc = assumptions.get("wacc")
    if isinstance(wacc, (int, float)):
        if wacc > 15.0:
            flags.append(
                {
                    "flag": "wacc_extreme_high",
                    "reason": f"WACC {wacc:.1f}% 는 대형주에 과도 — 정상 범위 초과",
                    "suggestedRetry": {"wacc": 9.0},
                }
            )
        elif wacc < 6.0:
            flags.append(
                {
                    "flag": "wacc_extreme_low",
                    "reason": f"WACC {wacc:.1f}% 는 지나치게 공격적 — 리스크 과소평가 가능",
                    "suggestedRetry": {"wacc": 9.0},
                }
            )

    # Kd (타인자본비용) — 회사채 수준 대비 과도
    kd = assumptions.get("kd")
    if isinstance(kd, (int, float)) and kd > 12.0:
        flags.append(
            {
                "flag": "kd_high",
                "reason": f"타인자본비용 Kd {kd:.1f}% 는 회사채 시장 대비 비현실적",
                "suggestedRetry": {"wacc": 9.0},
            }
        )

    # 영구성장률
    tg = assumptions.get("terminalGrowth")
    if isinstance(tg, (int, float)):
        if tg > 4.0:
            flags.append(
                {
                    "flag": "tg_extreme_high",
                    "reason": f"영구성장률 {tg:.1f}% 는 장기 GDP 성장률 초과 — 구조적 과대",
                    "suggestedRetry": {"terminalGrowth": 2.5},
                }
            )
        elif tg <= 0:
            flags.append(
                {
                    "flag": "tg_negative",
                    "reason": f"영구성장률 {tg:.1f}% 음수 — 소멸 가정",
                    "suggestedRetry": {"terminalGrowth": 2.0},
                }
            )

    # 부채비율
    debt = assumptions.get("debtRatio")
    if isinstance(debt, (int, float)):
        if debt > 200.0:
            flags.append(
                {
                    "flag": "debt_high",
                    "reason": f"부채비율 {debt:.0f}% 는 경계 수준 — 스트레스 시나리오 점검 필요",
                    "suggestedRetry": {"debtRatio": debt * 1.3, "scenarioStress": "severe"},
                }
            )

    # 이자보상배율
    icr = assumptions.get("interestCoverage")
    if isinstance(icr, (int, float)) and icr < 1.5:
        flags.append(
            {
                "flag": "icr_weak",
                "reason": f"이자보상배율 {icr:.2f}x — 영업이익으로 이자도 못 버는 경계",
                "suggestedRetry": {"interestCoverage": max(icr * 0.7, 0.5), "scenarioStress": "severe"},
            }
        )

    # 매크로 사이클
    phase = assumptions.get("cyclePhase")
    if phase in ("contraction", "trough"):
        flags.append(
            {
                "flag": "macro_stress",
                "reason": f"매크로 사이클 {phase} — 스트레스 시나리오 비교 권장",
                "suggestedRetry": {"cyclePhase": "contraction"},
            }
        )

    # ── 생애주기 ↔ 성장 지표 모순 검사 (Damodaran Corporate Life Cycle) ──
    lc_phase = assumptions.get("lifeCyclePhase")
    cagr = assumptions.get("revenueCAGR")
    if lc_phase == "decline" and isinstance(cagr, (int, float)) and cagr > 15.0:
        flags.append(
            {
                "flag": "lifecycle_conflict",
                "reason": f"생애주기 decline 판정인데 매출 CAGR {cagr:.1f}% — turnaround 재진입 가능성",
                "suggestedRetry": {"lifeCyclePhase": "turnaround"},
            }
        )
    elif lc_phase == "matureStable" and isinstance(cagr, (int, float)) and cagr > 20.0:
        flags.append(
            {
                "flag": "lifecycle_conflict",
                "reason": f"matureStable 판정인데 CAGR {cagr:.1f}% — highGrowth 재평가",
                "suggestedRetry": {"lifeCyclePhase": "highGrowth"},
            }
        )
    elif lc_phase in ("earlyGrowth", "highGrowth") and isinstance(cagr, (int, float)) and cagr < 0:
        flags.append(
            {
                "flag": "lifecycle_conflict",
                "reason": f"{lc_phase} 판정인데 CAGR {cagr:.1f}% — 구조조정 가능성",
                "suggestedRetry": {"lifeCyclePhase": "turnaround"},
            }
        )

    # pSurvival 하한 검증 — AI 가 자의적으로 0.1 등 극단값 주입 방지
    p_surv = assumptions.get("pSurvival")
    if isinstance(p_surv, (int, float)):
        if p_surv < 0.30:
            flags.append(
                {
                    "flag": "survival_extreme_low",
                    "reason": f"pSurvival {p_surv:.2f} 는 사실상 청산 가정 — liquidation 모델 직접 선택 권장",
                    "suggestedRetry": {"primaryModel": "liquidation"},
                }
            )
        elif p_surv > 1.0:
            flags.append(
                {
                    "flag": "survival_invalid",
                    "reason": f"pSurvival {p_surv:.2f} > 1 (확률 범위 초과)",
                    "suggestedRetry": {"pSurvival": 0.99},
                }
            )

    # ── Phase 3 규칙 ──
    # Implied ERP 가 historical 과 ±3%p 초과 이탈
    implied = assumptions.get("impliedERP")
    historical = assumptions.get("historicalERP")
    if isinstance(implied, (int, float)) and isinstance(historical, (int, float)):
        if abs(implied - historical) > 3.0:
            flags.append(
                {
                    "flag": "implied_far_from_historical",
                    "reason": f"Implied ERP {implied:.1f}% vs historical {historical:.1f}% — 시장 과열/공포 가능성",
                    "suggestedRetry": {"impliedERP": False},
                }
            )

    # Bottom-up beta peer 부족
    peer_count = assumptions.get("peerCount")
    if isinstance(peer_count, int) and peer_count < 5:
        flags.append(
            {
                "flag": "peer_count_low",
                "reason": f"Bottom-up beta peer {peer_count}개 — 섹터 기본값 사용 권장",
                "suggestedRetry": {"bottomUpBeta": False},
            }
        )

    # Control + Synergy 이중계산 위험
    control_premium = assumptions.get("controlPremium")
    synergy = assumptions.get("synergy")
    standalone = assumptions.get("standaloneValue")
    if (
        isinstance(control_premium, (int, float))
        and isinstance(synergy, (int, float))
        and isinstance(standalone, (int, float))
        and standalone > 0
    ):
        total_extra = control_premium + synergy
        if total_extra > standalone * 0.5:
            flags.append(
                {
                    "flag": "control_synergy_double_count",
                    "reason": f"Control premium + Synergy = {total_extra:,.0f} 이 standalone × 50% 초과 — 이중계산 의심",
                    "suggestedRetry": {"synergyType": "cost"},  # 최소 시너지로 축소
                }
            )

    return flags


def describeOverrides(engine: str) -> str:
    """tool schema description 용 override 키 요약.

    AI 가 `overrides={...}` 를 어떤 키로 채울 수 있는지 명시.
    """
    if engine == "analysis":
        return (
            "엔진 계산 가정을 직접 교체하는 dict. AI 가 비현실적 가정을 발견하면 재호출로 조율. "
            f"FORECAST: {sorted(FORECAST_KEYS)}, "
            f"VALUATION: {sorted(VALUATION_KEYS)}, "
            f"ANALYSIS: {sorted(ANALYSIS_KEYS)}. "
            "예: {'wacc': 9.0, 'terminalGrowth': 2.5}"
        )
    if engine == "credit":
        return (
            "신용평가 시나리오 가정을 교체. "
            f"키: {sorted(CREDIT_KEYS)}. "
            "예: {'debtRatio': 120, 'interestCoverage': 3.5}"
        )
    if engine == "quant":
        return f"기술적 분석 파라미터를 교체. 키: {sorted(QUANT_KEYS)}. 예: {{'window': 20, 'threshold': 70}}"
    if engine == "macro":
        return f"매크로 시나리오를 강제. 키: {sorted(MACRO_KEYS)}. 예: {{'cyclePhase': 'contraction'}}"
    return f"override dict. 키: {sorted(ALL_KEYS)}"
