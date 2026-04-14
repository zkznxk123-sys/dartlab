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
}

VALUATION_KEYS = {
    "wacc",  # float — WACC (%). None이면 CAPM 자동
    "terminalGrowth",  # float — 영구성장률 (%). None이면 업종 기본
    "primaryModel",  # str — "dcf"/"rim"/"ddm"/"relative". None이면 자동 선택
    "riskFreeRate",  # float — 무위험수익률 (%)
    "equityRiskPremium",  # float — 시장 리스크 프리미엄 (%)
    "beta",  # float — beta 계수
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
            flags.append({
                "flag": "wacc_extreme_high",
                "reason": f"WACC {wacc:.1f}% 는 대형주에 과도 — 정상 범위 초과",
                "suggestedRetry": {"wacc": 9.0},
            })
        elif wacc < 6.0:
            flags.append({
                "flag": "wacc_extreme_low",
                "reason": f"WACC {wacc:.1f}% 는 지나치게 공격적 — 리스크 과소평가 가능",
                "suggestedRetry": {"wacc": 9.0},
            })

    # Kd (타인자본비용) — 회사채 수준 대비 과도
    kd = assumptions.get("kd")
    if isinstance(kd, (int, float)) and kd > 12.0:
        flags.append({
            "flag": "kd_high",
            "reason": f"타인자본비용 Kd {kd:.1f}% 는 회사채 시장 대비 비현실적",
            "suggestedRetry": {"wacc": 9.0},
        })

    # 영구성장률
    tg = assumptions.get("terminalGrowth")
    if isinstance(tg, (int, float)):
        if tg > 4.0:
            flags.append({
                "flag": "tg_extreme_high",
                "reason": f"영구성장률 {tg:.1f}% 는 장기 GDP 성장률 초과 — 구조적 과대",
                "suggestedRetry": {"terminalGrowth": 2.5},
            })
        elif tg <= 0:
            flags.append({
                "flag": "tg_negative",
                "reason": f"영구성장률 {tg:.1f}% 음수 — 소멸 가정",
                "suggestedRetry": {"terminalGrowth": 2.0},
            })

    # 부채비율
    debt = assumptions.get("debtRatio")
    if isinstance(debt, (int, float)):
        if debt > 200.0:
            flags.append({
                "flag": "debt_high",
                "reason": f"부채비율 {debt:.0f}% 는 경계 수준 — 스트레스 시나리오 점검 필요",
                "suggestedRetry": {"debtRatio": debt * 1.3, "scenarioStress": "severe"},
            })

    # 이자보상배율
    icr = assumptions.get("interestCoverage")
    if isinstance(icr, (int, float)) and icr < 1.5:
        flags.append({
            "flag": "icr_weak",
            "reason": f"이자보상배율 {icr:.2f}x — 영업이익으로 이자도 못 버는 경계",
            "suggestedRetry": {"interestCoverage": max(icr * 0.7, 0.5), "scenarioStress": "severe"},
        })

    # 매크로 사이클
    phase = assumptions.get("cyclePhase")
    if phase in ("contraction", "trough"):
        flags.append({
            "flag": "macro_stress",
            "reason": f"매크로 사이클 {phase} — 스트레스 시나리오 비교 권장",
            "suggestedRetry": {"cyclePhase": "contraction"},
        })

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
