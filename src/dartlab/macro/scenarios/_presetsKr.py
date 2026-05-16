"""macro/scenarios/presets KR + DFAST 시나리오 분리.

presets.py 가 822 줄 god module 이라 KR + 미연준 DFAST 시나리오 dict 분리.
identity 보존을 위해 presets.py 가 본 모듈에서 re-export 한다.

상수:
- KR_SCENARIOS — 한국 특화 시나리오 (환율 위기, KOSPI 급락 등)
- DFAST_SCENARIOS — 미연준 Dodd-Frank Act Stress Test 시나리오
"""

from __future__ import annotations

# ══════════════════════════════════════

KR_SCENARIOS: dict[str, dict] = {
    "환율 위기": {
        "description": "원/달러 급등 — 자본유출 + 수입물가 급등",
        "transmission": "환율 급등 → 자본유출 → 수입물가 상승 → 금리인상 압력 → 가계부채 이자부담 → 소비 위축",
        "reference": "1997 IMF, IMF Korea FSAP (2020)",
        "mild": {"usdkrw": 1450, "hy_spread": 400, "cpi_yoy": 4.0},
        "moderate": {"usdkrw": 1550, "hy_spread": 600, "cpi_yoy": 5.0, "vix": 35},
        "severe": {"usdkrw": 1700, "hy_spread": 900, "cpi_yoy": 7.0, "vix": 50, "base_rate": 5.0},
        "extreme": {"usdkrw": 1900, "hy_spread": 1500, "cpi_yoy": 10.0, "vix": 65, "base_rate": 10.0},
    },
    "가계부채 위기": {
        "description": "DSR 급등 — 부동산 가격 하락 + 가계 디레버리징",
        "transmission": "금리 인상 → DSR 급등 → 소비 위축 → 부동산 하락 → 은행 부실 → 신용 경색",
        "reference": "IMF Korea FSAP (2020), BOK 금융안정보고서",
        "mild": {"base_rate": 4.5, "apt_yoy": -5, "hy_spread": 400},
        "moderate": {"base_rate": 5.5, "apt_yoy": -15, "hy_spread": 600, "unrate": 5.0},
        "severe": {"base_rate": 6.0, "apt_yoy": -25, "hy_spread": 900, "unrate": 7.0},
        "extreme": {"base_rate": 7.0, "apt_yoy": -40, "hy_spread": 1500, "unrate": 10.0},
    },
    "수출 급감": {
        "description": "글로벌 수요 붕괴 — 반도체/자동차 수출 급락",
        "transmission": "수출 급감 → 기업 이익 악화 → 고용 감소 → 소비 위축 → 환율 약세",
        "reference": "2009 금융위기, 2020 COVID",
        "mild": {"indpro_yoy": -3.0, "usdkrw": 1400},
        "moderate": {"indpro_yoy": -8.0, "usdkrw": 1500, "hy_spread": 500},
        "severe": {"indpro_yoy": -15.0, "usdkrw": 1600, "hy_spread": 800, "unrate": 6.0},
        "extreme": {"indpro_yoy": -25.0, "usdkrw": 1800, "hy_spread": 1200, "unrate": 9.0},
    },
    "북한 리스크": {
        "description": "한반도 군사적 긴장 고조 — 외국인 자본 이탈",
        "transmission": "지정학 리스크 → 외국인 매도 → KOSPI 급락 + 원화 약세 → 금리 방어 → 경기 위축",
        "reference": "2017 북한 핵실험, 2010 천안함/연평도",
        "mild": {"usdkrw": 1400, "vix": 30, "kospi_change": -10},
        "moderate": {"usdkrw": 1500, "vix": 40, "kospi_change": -20, "hy_spread": 500},
        "severe": {"usdkrw": 1650, "vix": 55, "kospi_change": -35, "hy_spread": 800, "base_rate": 5.0},
        "extreme": {"usdkrw": 1900, "vix": 75, "kospi_change": -50, "hy_spread": 1500, "base_rate": 8.0},
    },
    "반도체 다운사이클": {
        "description": "글로벌 반도체 수요 급감 — 삼성/SK 실적 직격",
        "transmission": "DRAM/NAND 가격 급락 → 반도체 기업 감산 → 수출 감소 → GDP 직격 → 관련 산업 연쇄",
        "reference": "2019 반도체 다운사이클, 2022-23 메모리 불황",
        "mild": {"indpro_yoy": -3.0, "usdkrw": 1380},
        "moderate": {"indpro_yoy": -8.0, "usdkrw": 1450, "kospi_change": -15},
        "severe": {"indpro_yoy": -15.0, "usdkrw": 1550, "kospi_change": -30, "hy_spread": 500},
        "extreme": {"indpro_yoy": -25.0, "usdkrw": 1700, "kospi_change": -45, "hy_spread": 800, "unrate": 6.0},
    },
    "중국 수요 급감": {
        "description": "중국 경기 급랭 — 한국 대중 수출 붕괴",
        "transmission": "중국 GDP 급락 → 대중 수출 -30%+ → 석유화학/철강/반도체 타격 → 기업이익 급감 → 고용 악화",
        "reference": "2015 중국 위안 절하 + 중국 부동산 위기 확대",
        "mild": {"indpro_yoy": -3.0, "usdkrw": 1400, "cpi_yoy": 1.0},
        "moderate": {"indpro_yoy": -7.0, "usdkrw": 1500, "hy_spread": 500, "vix": 35},
        "severe": {"indpro_yoy": -12.0, "usdkrw": 1600, "hy_spread": 700, "vix": 45, "unrate": 5.5},
        "extreme": {"indpro_yoy": -20.0, "usdkrw": 1750, "hy_spread": 1000, "vix": 60, "unrate": 8.0},
    },
}

# ══════════════════════════════════════
# Fed DFAST 공식 시나리오 (2026)
# ══════════════════════════════════════

DFAST_SCENARIOS: dict[str, dict] = {
    "DFAST Baseline": {
        "description": "Fed 공식 기준 시나리오 — 완만한 성장 지속",
        "period": "가상 (Fed 2026 시나리오)",
        "type": "기준",
        "severity": "mild",
        "reference": "Federal Reserve 2026 Stress Test Scenarios",
        "overrides": {
            "unrate": 4.5,
            "vix": 18,
            "hy_spread": 350,
            "fedfunds": 3.5,
            "term_spread": 0.8,
            "cpi_yoy": 2.3,
            "indpro_yoy": 1.5,
        },
        "outcome": "GDP +2.2%, 실업률 4.5%. 점진적 금리 인하. 안정적 성장.",
    },
    "DFAST Adverse": {
        "description": "Fed 공식 역경 시나리오 — 글로벌 경기 둔화",
        "period": "가상 (Fed 2026 시나리오)",
        "type": "복합 충격",
        "severity": "severe",
        "reference": "Federal Reserve 2026 Stress Test Scenarios",
        "overrides": {
            "unrate": 7.2,
            "vix": 50,
            "hy_spread": 350,  # 3.5pp
            "fedfunds": 1.0,
            "term_spread": 2.0,
            "cpi_yoy": 1.5,
            "sp500_change": -38,
            "indpro_yoy": -5.0,
        },
        "outcome": "GDP -2.8%, 실업률 7.2%, 주가 -38%, 주택 -18%.",
    },
    "DFAST Severely Adverse": {
        "description": "Fed 공식 극심 시나리오 — 극심한 글로벌 침체",
        "period": "가상 (Fed 2026 시나리오)",
        "type": "복합 충격",
        "severity": "extreme",
        "reference": "Federal Reserve 2026 Stress Test Scenarios",
        "overrides": {
            "unrate": 10.0,
            "vix": 72,
            "hy_spread": 570,
            "fedfunds": 0.1,
            "term_spread": 3.0,
            "cpi_yoy": 1.0,
            "sp500_change": -58,
            "indpro_yoy": -8.0,
        },
        "outcome": "GDP -4.6%, 실업률 10%, 주가 -58%, 주택 -30%, 상업용부동산 -39%.",
    },
}


# ══════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════


__all__ = ["DFAST_SCENARIOS", "KR_SCENARIOS"]
