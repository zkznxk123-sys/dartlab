"""Analysis Override 표준 — AI/사용자가 분석 가정을 조율하는 인터페이스.

Level 1 (시스템 디폴트): overrides=None → 자동 계산
Level 2 (AI/사용자 조율): overrides={...} → 지정 가정만 교체, 나머지 자동

4개 엔진(analysis/credit/quant/macro) 전부 동일 패턴.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Override 키 정의 ──

FORECAST_KEYS = {
    "baseRevenue",      # float — 기준 매출 (원). None이면 자동 (TTM 또는 mid-cycle)
    "growthRates",      # list[float] — 연도별 매출 성장률 (%). None이면 forecast 엔진 자동
    "opm",              # float — 영업이익률 (0.0~1.0). None이면 과거 추세
    "capexRatio",       # float — CAPEX/매출 (0.0~1.0). None이면 과거 평균
    "depreciationRatio",# float — 감가상각/매출
    "nwcRatio",         # float — 운전자본/매출
    "taxRate",          # float — 유효세율
}

VALUATION_KEYS = {
    "wacc",             # float — WACC (%). None이면 자동
    "terminalGrowth",   # float — 영구성장률 (%). None이면 업종 기본
    "primaryModel",     # str — "dcf"/"rim"/"ddm"/"relative". None이면 자동 선택
}

CREDIT_KEYS = {
    "debtRatio",        # float — 시나리오 부채비율 (%)
    "interestCoverage", # float — 시나리오 이자보상배율
}

MACRO_KEYS = {
    "cyclePhase",       # str — 사이클 국면 override
}

ALL_KEYS = FORECAST_KEYS | VALUATION_KEYS | CREDIT_KEYS | MACRO_KEYS


def validateOverrides(overrides: dict | None) -> dict:
    """override dict 검증 + 정규화. 잘못된 키는 경고 후 무시."""
    if not overrides:
        return {}

    clean: dict = {}
    for key, value in overrides.items():
        if key not in ALL_KEYS:
            continue  # 미인식 키 무시
        if value is None:
            continue  # None은 "자동"과 동일
        clean[key] = value

    return clean


def applyOverride(auto_value: Any, override_key: str, overrides: dict) -> Any:
    """자동 계산 값에 override 적용. override 없으면 auto_value 반환."""
    if not overrides or override_key not in overrides:
        return auto_value
    return overrides[override_key]
