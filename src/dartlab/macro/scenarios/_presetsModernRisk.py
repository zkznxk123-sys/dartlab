"""현대적 리스크 시나리오 (6 개) — 발생 가능 충격 × 4 심각도.

각 시나리오는 mild/moderate/severe/extreme 4 단계 override dict 제공.
"AI 버블", "중국 디플레", "일본식 장기침체", "대만 해협", "글로벌 무역전쟁",
"미국 국채 위기" — 학술 + 정성적 추정 기반 미발생 시나리오.

본 모듈은 데이터 정의만 담는다. 호출 로직은 ``presets.py``.
"""

from __future__ import annotations

MODERN_RISK_SCENARIOS: dict[str, dict] = {
    "AI 버블 붕괴": {
        "description": "AI 과잉투자 → 수익 실현 실패 → 기술주 폭락",
        "type": "자산 버블 붕괴",
        "transmission": "기술주 폭락 → HY 확대(기술 기업 부채) → VC/PE 손실 → 신용 경색 확산",
        "reference": "2001 IT버블 패턴 + 현대 AI 투자 규모",
        "mild": {"sp500_change": -20, "vix": 35, "hy_spread": 500},
        "moderate": {"sp500_change": -35, "vix": 50, "hy_spread": 700, "nfci": 0.5},
        "severe": {"sp500_change": -50, "vix": 65, "hy_spread": 1000, "nfci": 1.5, "unrate": 7.0},
        "extreme": {"sp500_change": -70, "vix": 80, "hy_spread": 1500, "nfci": 2.5, "unrate": 9.0, "indpro_yoy": -5.0},
    },
    "중국 디플레이션": {
        "description": "중국 부동산 붕괴 + 디플레이션 수출 → 글로벌 수요 위축",
        "type": "디플레이션",
        "transmission": "중국 수요 붕괴 → 원자재 가격 하락 → EM 수출 급감 → 글로벌 산업생산 위축",
        "reference": "일본 1990년대 + 중국 2024~ 부동산 위기",
        "mild": {"indpro_yoy": -2.0, "cpi_yoy": 1.0},
        "moderate": {"indpro_yoy": -5.0, "cpi_yoy": 0.5, "hy_spread": 500, "vix": 30},
        "severe": {"indpro_yoy": -10.0, "cpi_yoy": -0.5, "hy_spread": 700, "vix": 40, "unrate": 6.0},
        "extreme": {"indpro_yoy": -15.0, "cpi_yoy": -2.0, "hy_spread": 1000, "vix": 55, "unrate": 8.0, "fedfunds": 0.5},
    },
    "일본식 장기침체": {
        "description": "재무상태표 침체 — 장기 저성장 + 제로금리 함정",
        "type": "디플레이션",
        "transmission": "자산 버블 붕괴 → 민간 디레버리징 → 소비/투자 장기 위축 → 제로금리에도 회복 안 됨",
        "reference": "Koo (2009) Balance Sheet Recession, 일본 1990~2010",
        "mild": {"fedfunds": 0.5, "cpi_yoy": 0.5, "indpro_yoy": 0.0, "term_spread": 0.5},
        "moderate": {"fedfunds": 0.1, "cpi_yoy": 0.0, "indpro_yoy": -1.0, "term_spread": 0.3, "unrate": 5.5},
        "severe": {
            "fedfunds": 0.0,
            "cpi_yoy": -0.5,
            "indpro_yoy": -3.0,
            "term_spread": 0.2,
            "unrate": 7.0,
            "hy_spread": 400,
        },
        "extreme": {
            "fedfunds": 0.0,
            "cpi_yoy": -1.5,
            "indpro_yoy": -5.0,
            "term_spread": 0.1,
            "unrate": 8.0,
            "hy_spread": 600,
        },
    },
    "대만 해협 분쟁": {
        "description": "미중 군사 대치 — 반도체 공급망 단절 + 글로벌 무역 마비",
        "type": "지정학/팬데믹",
        "transmission": "군사 대치 → VIX 급등 + 안전자산 쏠림 → 반도체 공급 단절 → 산업생산 마비 → 글로벌 침체",
        "reference": "2020 COVID 공급 충격 + 1973 오일쇼크 규모",
        "mild": {"vix": 45, "hy_spread": 600, "indpro_yoy": -5.0},
        "moderate": {"vix": 60, "hy_spread": 900, "indpro_yoy": -10.0, "cpi_yoy": 6.0, "nfci": 1.0},
        "severe": {"vix": 75, "hy_spread": 1200, "indpro_yoy": -18.0, "cpi_yoy": 8.0, "nfci": 2.0, "unrate": 9.0},
        "extreme": {"vix": 90, "hy_spread": 2000, "indpro_yoy": -25.0, "cpi_yoy": 12.0, "nfci": 3.0, "unrate": 12.0},
    },
    "글로벌 무역전쟁": {
        "description": "미중 관세 전면전 + WTO 체제 붕괴",
        "type": "지정학/팬데믹",
        "transmission": "관세 급등 → 수입물가 상승 → 공급망 재편 비용 → 산업생산 위축 → 스태그플레이션",
        "reference": "2018-19 미중 무역분쟁 확대 버전",
        "mild": {"cpi_yoy": 4.0, "indpro_yoy": -2.0, "vix": 30},
        "moderate": {"cpi_yoy": 5.5, "indpro_yoy": -5.0, "vix": 40, "hy_spread": 500},
        "severe": {"cpi_yoy": 7.0, "indpro_yoy": -8.0, "vix": 50, "hy_spread": 700, "unrate": 6.0},
        "extreme": {"cpi_yoy": 10.0, "indpro_yoy": -15.0, "vix": 65, "hy_spread": 1000, "unrate": 9.0},
    },
    "미국 국채 위기": {
        "description": "미국 재정적자 급증 → 국채 수요 급감 → 금리 급등",
        "type": "금리 충격",
        "transmission": "국채 매도 → 장기금리 급등 → 모기지/기업 차입 비용 폭증 → 부동산/기업 동시 위기",
        "reference": "2011 미국 신용등급 강등 + 영국 2022 미니버짓 위기",
        "mild": {"term_spread": 2.0, "fedfunds": 5.5, "vix": 30, "hy_spread": 500},
        "moderate": {"term_spread": 3.0, "fedfunds": 6.0, "vix": 45, "hy_spread": 700},
        "severe": {"term_spread": 4.0, "fedfunds": 7.0, "vix": 55, "hy_spread": 1000, "unrate": 7.0},
        "extreme": {"term_spread": 5.0, "fedfunds": 8.0, "vix": 70, "hy_spread": 1500, "unrate": 10.0},
    },
}

__all__ = ["MODERN_RISK_SCENARIOS"]
